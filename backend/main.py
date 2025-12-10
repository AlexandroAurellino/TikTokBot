# backend/main.py

import threading
import logging
import time
from flask import Flask, render_template, request, jsonify
from pathlib import Path

from engine import MainApplication
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Flask Setup
project_root = Path(__file__).parent.parent
template_folder = project_root / 'frontend' / 'templates'
static_folder = project_root / 'frontend' / 'static'

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

# Global state
app_instance = None
app_thread = None
thread_lock = threading.Lock()


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
                logging.info("Settings saved to database successfully.")
                return jsonify({"status": "success", "message": "Settings saved!"})
            else:
                return jsonify({"status": "error", "message": "Failed to save to database."}), 500
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the main application."""
    global app_instance, app_thread
    
    with thread_lock:
        if app_thread and app_thread.is_alive():
            return jsonify({"status": "error", "message": "Bot is already running."}), 400
        
        try:
            logging.info("Starting bot from dashboard...")
            app_instance = MainApplication()
            
            # Start returns False if OBS connection fails
            if not app_instance.start():
                app_instance = None
                return jsonify({"status": "error", "message": "Failed to connect to OBS. Check settings."}), 500
            
            # The start() method launches its own thread internally
            # We just need to keep a reference to the instance
            return jsonify({"status": "success", "message": "Bot started successfully!"})
            
        except Exception as e:
            logging.error(f"Failed to start bot: {e}")
            app_instance = None
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the main application."""
    global app_instance, app_thread
    
    with thread_lock:
        if not app_instance:
            return jsonify({"status": "error", "message": "Bot is not running."}), 400
        
        try:
            logging.info("Stopping bot from dashboard...")
            
            # Call stop which handles all cleanup
            app_instance.stop()
            
            # Wait briefly for threads to finish
            time.sleep(2)
            
            # Clear references
            app_instance = None
            app_thread = None
            
            return jsonify({"status": "success", "message": "Bot stopped successfully!"})
            
        except Exception as e:
            logging.error(f"Error stopping bot: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get bot status, stats, and logs."""
    global app_instance
    
    # Check if bot is running by checking if instance exists and stop_event is not set
    is_running = app_instance is not None and not app_instance.stop_event.is_set()
    
    response = {
        "running": is_running,
        "stats": None,
        "logs": []
    }
    
    if is_running and app_instance:
        try:
            data = app_instance.get_data()
            response["stats"] = data["stats"]
            response["logs"] = data["logs"]
        except Exception as e:
            logging.error(f"Error getting status data: {e}")
    
    return jsonify(response)


if __name__ == '__main__':
    print("=" * 60)
    print(">>> AI Scene Changer Control Panel <<<")
    print(">>> Open your browser to: http://127.0.0.1:5000 <<<")
    print("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        # Cleanup on exit
        if app_instance:
            try:
                app_instance.stop()
            except:
                pass