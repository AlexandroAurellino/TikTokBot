from flask import Flask
from flask_socketio import SocketIO
from config import TEMPLATE_DIR, STATIC_DIR, MEDIA_FOLDER, SECRET_KEY

# Initialize SocketIO globally (but don't attach to app yet)
socketio = SocketIO(async_mode='threading', cors_allowed_origins="*")

def create_app():
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['UPLOAD_FOLDER'] = MEDIA_FOLDER

    # Initialize SocketIO with this app
    socketio.init_app(app)

    # Register Blueprints/Routes
    from web.routes import main_bp
    app.register_blueprint(main_bp)

    return app