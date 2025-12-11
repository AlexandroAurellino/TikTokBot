import os
from flask import Blueprint, render_template, request, jsonify, send_from_directory, current_app
from werkzeug.utils import secure_filename
from web import socketio
from core.engine import MainApplication
from core import database

# Create a Blueprint
main_bp = Blueprint('main', __name__)

# Global reference to the bot (managed within this module)
bot_instance = None

@main_bp.route('/')
def index():
    return render_template('index.html')

# --- MEDIA ROUTES ---
@main_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        return jsonify({"status": "success", "filename": filename})

@main_bp.route('/api/media', methods=['GET'])
def list_media():
    folder = current_app.config['UPLOAD_FOLDER']
    try:
        files = [f for f in os.listdir(folder) if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm'))]
        return jsonify(files)
    except: return jsonify([])

@main_bp.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

# --- SETTINGS ROUTES ---
@main_bp.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    if request.method == 'GET':
        return jsonify(database.load_settings())
    elif request.method == 'POST':
        if database.save_settings(request.json):
            return jsonify({"status": "success"})
        return jsonify({"status": "error"}), 500

# --- CONTROL ROUTES ---
@main_bp.route('/api/control', methods=['POST'])
def control_bot():
    global bot_instance
    action = request.json.get('action')
    
    if action == 'start':
        if bot_instance: return jsonify({"status": "error", "message": "Running"}), 400
        
        # Initialize Engine with SocketIO and Media Path
        bot_instance = MainApplication(
            socketio_instance=socketio, 
            upload_folder=current_app.config['UPLOAD_FOLDER']
        )
        if bot_instance.start():
            return jsonify({"status": "success"})
        else:
            bot_instance = None
            return jsonify({"status": "error", "message": "OBS Error"}), 500

    elif action == 'stop':
        if bot_instance:
            bot_instance.stop()
            bot_instance = None
        return jsonify({"status": "success"})
            
    return jsonify({"status": "error"}), 400

@main_bp.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"running": bot_instance is not None})

@socketio.on('connect')
def handle_connect():
    if bot_instance: bot_instance.emit_stats()

@main_bp.route('/api/control/skip', methods=['POST'])
def skip_video():
    if bot_instance and bot_instance.skip_current():
        return jsonify({"status": "success", "message": "Skipped"})
    return jsonify({"status": "error", "message": "Nothing playing or bot stopped"})

@main_bp.route('/api/control/play', methods=['POST'])
def manual_play():
    product_name = request.json.get('product_name')
    if bot_instance:
        bot_instance.manual_play(product_name)
        return jsonify({"status": "success", "message": f"Queued {product_name}"})
    return jsonify({"status": "error", "message": "Bot is not running"})