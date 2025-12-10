# backend/main.py

import threading
import logging
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from pathlib import Path

from engine import MainApplication
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Flask & SocketIO Setup
project_root = Path(__file__).parent.parent
template_folder = project_root / 'frontend' / 'templates'
static_folder = project_root / 'frontend' / 'static'

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['SECRET_KEY'] = 'secret_key_for_session' 

# Initialize SocketIO. async_mode='threading' is easiest for compatibility with our other threads
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Global reference
bot_instance = None

@app.route('/')
def index():
    """Serve the main dashboard HTML page."""
    return render_template('index.html')

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

@app.route('/api/control', methods=['POST'])
def control_bot():
    """Start or Stop the bot."""
    global bot_instance
    action = request.json.get('action')
    
    if action == 'start':
        if bot_instance:
            return jsonify({"status": "error", "message": "Bot is already running"}), 400
        
        # Create new instance, passing socketio so it can emit logs
        bot_instance = MainApplication(socketio_instance=socketio)
        
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
    """Simple status check for initial load."""
    running = bot_instance is not None
    return jsonify({"running": running})

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    print("Client connected via WebSocket")
    # If bot is running, send current stats immediately
    if bot_instance:
        bot_instance.emit_stats()

if __name__ == '__main__':
    print("=" * 60)
    print(">>> AI Scene Changer Control Panel <<<")
    print(">>> Open: http://127.0.0.1:5000 <<<")
    print("=" * 60)
    
    # Use socketio.run instead of app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)