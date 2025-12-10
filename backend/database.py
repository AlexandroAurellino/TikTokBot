#backend/database.py

print("!!! DATABASE MODULE LOADED SUCCESSFULLY !!!")
import sqlite3
import logging
import json
from pathlib import Path

# Define the database file path
DB_PATH = Path(__file__).parent.parent / 'app.db'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scene TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Migration check
    try:
        c.execute('SELECT description FROM products LIMIT 1')
    except sqlite3.OperationalError:
        print("⚠️ upgrading database schema: adding description column")
        c.execute('ALTER TABLE products ADD COLUMN description TEXT')

    # Defaults
    defaults = {
        "tiktok_username": "@username",
        "deepseek_api_key": "",
        "main_scene_name": "Scene_A",
        "obs_ws_host": "localhost",
        "obs_ws_port": "4455",
        "obs_ws_password": "",
        "comment_rate_limit": "2",
        "tiktok_reconnect_delay": "30",
        "cache_duration_seconds": "300"
    }
    
    c.execute('SELECT count(*) FROM settings')
    if c.fetchone()[0] == 0:
        for key, val in defaults.items():
            c.execute('INSERT INTO settings (key, value) VALUES (?, ?)', (key, val))
        
    conn.commit()
    conn.close()

def load_settings():
    """Retrieves full configuration as a dictionary."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT key, value FROM settings')
    config = {row['key']: row['value'] for row in c.fetchall()}
    
    c.execute('SELECT name, scene, description FROM products')
    db_products = c.fetchall()
    
    conn.close()
    
    # Type conversion
    try:
        config['obs_ws_port'] = int(config.get('obs_ws_port', 4455))
        config['comment_rate_limit'] = int(config.get('comment_rate_limit', 2))
        config['tiktok_reconnect_delay'] = int(config.get('tiktok_reconnect_delay', 30))
        config['cache_duration_seconds'] = int(config.get('cache_duration_seconds', 300))
    except ValueError:
        pass 

    products_list_obj = []
    for row in db_products:
        products_list_obj.append({
            "name": row['name'],
            "scene": row['scene'],
            "description": row['description'] if row['description'] else ""
        })
    config['products'] = products_list_obj
    config['product_list'] = [p['name'] for p in products_list_obj]
    config['product_to_scene_map'] = {p['name']: p['scene'] for p in products_list_obj}
    
    return config

def save_settings(data):
    """Saves settings and products to the database."""
    print("\n" + "="*50)
    print("----- DEBUG: BACKEND RECEIVED DATA -----")
    print(f"KEYS RECEIVED: {list(data.keys())}")
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 1. Update General Settings
        keys_to_save = [
            "tiktok_username", "deepseek_api_key", "main_scene_name",
            "obs_ws_host", "obs_ws_port", "obs_ws_password",
            "comment_rate_limit", "tiktok_reconnect_delay", "cache_duration_seconds"
        ]
        
        for key in keys_to_save:
            if key in data:
                c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', 
                          (key, str(data[key])))
        
        # 2. Update Products
        if 'products' in data:
            incoming_products = data['products']
            print(f"DEBUG: Found 'products' key. Count: {len(incoming_products)}")
            
            c.execute('DELETE FROM products')
            
            for prod in incoming_products:
                name = prod.get('name')
                scene = prod.get('scene')
                # Debug print for EACH item
                print(f"DEBUG: Processing Item -> {name} | {scene}")
                
                # Make sure we handle missing descriptions gracefully
                desc = prod.get('description', '')
                
                if name and scene:
                    c.execute('INSERT INTO products (name, scene, description) VALUES (?, ?, ?)',
                              (name, scene, desc))
        else:
            print("DEBUG: 'products' key MISSING in data")

        conn.commit()
        print("----- DEBUG: SAVE COMPLETE -----\n" + "="*50 + "\n")
        return True
    except Exception as e:
        logging.error(f"Database save error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Initialize immediately
init_db()