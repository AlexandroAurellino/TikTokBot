import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / 'frontend'
TEMPLATE_DIR = FRONTEND_DIR / 'templates'
STATIC_DIR = FRONTEND_DIR / 'static'
MEDIA_FOLDER = BASE_DIR / 'media'
DB_PATH = BASE_DIR / 'app.db'

# Ensure Media Folder Exists
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# App Config
SECRET_KEY = "murah_sehat"