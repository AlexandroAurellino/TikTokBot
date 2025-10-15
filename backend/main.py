# backend/main.py

import json
import threading
import logging
from flask import Flask, render_template, request, jsonify
from pathlib import Path

# Import our existing engine
from engine import MainApplication

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Flask App Setup ---
project_root = Path(__file__).parent.parent
template_folder = project_root / 'frontend' / 'templates'
static_folder = project_root / 'frontend' / 'static'

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
config_path = project_root / 'config.json'

# --- Global variables to manage the engine thread ---
app_instance = None
app_thread = None
thread_lock = threading.Lock()

# --- Helper Functions ---

def validate_settings(settings: dict) -> tuple[bool, str]:
    """
    Validates the settings dictionary.
    
    Returns:
        (is_valid, error_message) tuple
    """
    # Check required fields
    required_fields = ['tiktok_username', 'deepseek_api_key', 'product_list', 'product_to_scene_map']
    for field in required_fields:
        if field not in settings or not settings[field]:
            return False, f"Missing required field: {field}"
    
    # Validate TikTok username format
    username = settings['tiktok_username']
    if not username.startswith('@'):
        settings['tiktok_username'] = '@' + username
    
    # Validate product_list is a list
    if not isinstance(settings['product_list'], list):
        return False, "product_list must be an array"
    
    # Validate product_to_scene_map is an object
    if not isinstance(settings['product_to_scene_map'], dict):
        return False, "product_to_scene_map must be an object"
    
    # Validate that product_list matches product_to_scene_map keys
    products = set(settings['product_list'])
    mapped_products = set(settings['product_to_scene_map'].keys())
    
    if products != mapped_products:
        missing_in_map = products - mapped_products
        extra_in_map = mapped_products - products
        error_msg = "Product list and scene map don't match. "
        if missing_in_map:
            error_msg += f"Missing in map: {missing_in_map}. "
        if extra_in_map:
            error_msg += f"Extra in map: {extra_in_map}."
        return False, error_msg
    
    # Validate port is a number
    if 'obs_ws_port' in settings:
        try:
            settings['obs_ws_port'] = int(settings['obs_ws_port'])
        except (ValueError, TypeError):
            return False, "obs_ws_port must be a number"
    
    return True, ""


# --- API Endpoints ---

@app.route('/')
def index():
    """Serve the main dashboard HTML page."""
    return render_template('index.html')


@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """API endpoint to load and save settings."""
    if request.method == 'GET':
        try:
            with open(config_path, 'r') as f:
                settings = json.load(f)
            return jsonify(settings)
        except FileNotFoundError:
            # Return default settings if config doesn't exist
            default_settings = {
                "tiktok_username": "@username",
                "deepseek_api_key": "",
                "obs_ws_host": "localhost",
                "obs_ws_port": 4455,
                "obs_ws_password": "",
                "main_scene_name": "Scene_A",
                "tiktok_reconnect_delay": 30,
                "comment_rate_limit": 2,
                "cache_duration_seconds": 300,
                "product_list": [],
                "product_to_scene_map": {}
            }
            return jsonify(default_settings)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON in config.json: {str(e)}"}), 400
    
    elif request.method == 'POST':
        try:
            new_settings = request.json
            
            # Validate settings
            is_valid, error_message = validate_settings(new_settings)
            if not is_valid:
                return jsonify({"error": error_message}), 400
            
            # Save to file
            with open(config_path, 'w') as f:
                json.dump(new_settings, f, indent=2)
            
            logging.info("Settings saved successfully")
            return jsonify({
                "status": "success",
                "message": "Settings saved successfully!"
            })
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format"}), 400
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            return jsonify({"error": f"Failed to save settings: {str(e)}"}), 500


@app.route('/api/start', methods=['POST'])
def start_bot():
    """API endpoint to start the main application in a background thread."""
    global app_instance, app_thread
    
    with thread_lock:
        # Check if already running
        if app_thread and app_thread.is_alive():
            return jsonify({
                "status": "error",
                "message": "Bot is already running."
            }), 400
        
        try:
            logging.info("Received start command from dashboard.")
            
            # Create new instance
            app_instance = MainApplication()
            
            # Start in background thread
            app_thread = threading.Thread(target=app_instance.start, daemon=True)
            app_thread.start()
            
            logging.info("Bot started successfully")
            return jsonify({
                "status": "success",
                "message": "Bot started successfully!"
            })
        except Exception as e:
            logging.error(f"Failed to start bot: {e}")
            app_thread = None
            app_instance = None
            return jsonify({
                "status": "error",
                "message": f"Failed to start bot: {str(e)}"
            }), 500


@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """API endpoint to stop the main application."""
    global app_instance, app_thread
    
    with thread_lock:
        # Check if running
        if not (app_thread and app_thread.is_alive()):
            return jsonify({
                "status": "error",
                "message": "Bot is not running."
            }), 400
        
        try:
            logging.info("Received stop command from dashboard.")
            
            # Stop the instance
            if app_instance:
                app_instance.stop()
            
            # Wait for thread to finish (with timeout)
            app_thread.join(timeout=5)
            
            # Clear references
            app_thread = None
            app_instance = None
            
            logging.info("Bot stopped successfully")
            return jsonify({
                "status": "success",
                "message": "Bot stopped successfully!"
            })
        except Exception as e:
            logging.error(f"Error stopping bot: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to stop bot: {str(e)}"
            }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """API endpoint to check if the bot is running and get statistics."""
    global app_instance, app_thread
    
    is_running = app_thread is not None and app_thread.is_alive()
    
    response = {
        "running": is_running,
        "stats": None
    }
    
    # Include statistics if bot is running
    if is_running and app_instance:
        try:
            response["stats"] = app_instance.get_stats()
        except Exception as e:
            logging.error(f"Error getting stats: {e}")
    
    return jsonify(response)


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """API endpoint to retrieve recent log entries."""
    # This is a placeholder - you'd need to implement log storage
    # For now, return empty array
    return jsonify({"logs": []})


# --- Error Handlers ---

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# --- Run the Web Server ---

if __name__ == '__main__':
    print("=" * 60)
    print(">>> Starting AI Scene Changer Control Panel <<<")
    print(">>> Open your browser to: http://127.0.0.1:5000 <<<")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)