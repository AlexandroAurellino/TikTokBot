import threading
import logging
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

from engine import MainApplication
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
project_root = Path(__file__).parent.parent
template_folder = project_root / 'frontend' / 'templates'
static_folder = project_root / 'frontend' / 'static'
upload_folder = project_root / 'media'

# Ensure media directory exists
os.makedirs(upload_folder, exist_ok=True)

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'secret_key_for_session' 
app.config['UPLOAD_FOLDER'] = upload_folder

# Initialize SocketIO
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Global reference
bot_instance = None

@app.route('/')
def index():
    """Serve the main dashboard HTML page."""
    return render_template('index.html')

# --- MEDIA ROUTES ---
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle video file uploads."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        logging.info(f"File uploaded: {filename}")
        return jsonify({"status": "success", "filename": filename})

@app.route('/api/media', methods=['GET'])
def list_media():
    """List available video files."""
    try:
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                 if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))]
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve video files for preview."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- SETTINGS ROUTES ---
@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Load and save settings via database."""
    if request.method == 'GET':
        settings = database.load_settings()
        return jsonify(settings)
    elif request.method == 'POST':
        try:
            new_settings = request.json
            if database.save_settings(new_settings):
                return jsonify({"status": "success", "message": "Settings saved!"})
            else:
                return jsonify({"status": "error", "message": "Failed to save to database."}), 500
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

# --- CONTROL ROUTES ---
@app.route('/api/control', methods=['POST'])
def control_bot():
    """Start or Stop the bot."""
    global bot_instance
    action = request.json.get('action')
    
    if action == 'start':
        if bot_instance:
            return jsonify({"status": "error", "message": "Bot is already running"}), 400
        
        # Pass socketio AND upload_folder to engine
        bot_instance = MainApplication(socketio_instance=socketio, upload_folder=app.config['UPLOAD_FOLDER'])
        
        if bot_instance.start():
            return jsonify({"status": "success", "message": "Bot started"})
        else:
            bot_instance = None
            return jsonify({"status": "error", "message": "Failed to start (Check OBS)"}), 500

    elif action == 'stop':
        if bot_instance:
            bot_instance.stop()
            bot_instance = None
            return jsonify({"status": "success", "message": "Bot stopped"})
        else:
            return jsonify({"status": "error", "message": "Bot not running"}), 400
            
    return jsonify({"status": "error", "message": "Invalid action"}), 400

@app.route('/api/status', methods=['GET'])
def get_status():
    """Simple status check."""
    running = bot_instance is not None
    return jsonify({"running": running})

# --- SOCKET EVENTS ---
@socketio.on('connect')
def handle_connect():
    print("Client connected via WebSocket")
    if bot_instance:
        bot_instance.emit_stats()

if __name__ == '__main__':
    print("=" * 60)
    print(">>> AI Scene Changer Control Panel <<<")
    print(">>> Open: http://127.0.0.1:5000 <<<")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)