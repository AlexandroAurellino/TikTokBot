# backend/engine.py

import logging
import time
import threading
import asyncio
from datetime import datetime
from difflib import SequenceMatcher

from obs_controller import OBSController
from ai_processor import AIProcessor
from tiktok_listener import TikTokListener
import database 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MainApplication:
    """The main application orchestrating all components."""
    
    def __init__(self, socketio_instance=None):
        self.socketio = socketio_instance 
        self.config = database.load_settings()
        self._init_settings()
        
        self.obs = OBSController(
            host=self.obs_host,
            port=self.obs_port,
            password=self.obs_password,
            event_callback=self.on_obs_event
        )
        
        if self.deepseek_api_key:
            self.ai = AIProcessor(api_key=self.deepseek_api_key)
        else:
            self.ai = None
            
        self.stop_event = threading.Event()
        self.thread = None
        self.current_listener = None
        
        self.auto_return_timer = None
        self.auto_return_delay = 30
        
        self.processed_cache = {} 
        self.rate_limit_timestamps = [] 
        
        self.stats = {
            'comments_processed': 0,
            'scenes_switched': 0, 
            'errors': 0
        }
        
    def _init_settings(self):
        self.tiktok_username = self.config.get("tiktok_username")
        self.product_list = self.config.get("product_list", [])
        self.product_to_scene_map = self.config.get("product_to_scene_map", {})
        self.main_scene_name = self.config.get("main_scene_name", "Scene_A")
        
        self.reconnect_delay = int(self.config.get("tiktok_reconnect_delay", 30))
        self.deepseek_api_key = self.config.get("deepseek_api_key")
        
        self.obs_host = self.config.get("obs_ws_host", "localhost")
        self.obs_port = int(self.config.get("obs_ws_port", 4455))
        self.obs_password = self.config.get("obs_ws_password", "")
        
        self.rate_limit = int(self.config.get("comment_rate_limit", 2))
        
        self.video_scenes = {
            scene for scene in self.product_to_scene_map.values() 
            if scene != self.main_scene_name
        }

    # --- WEBSOCKET HELPERS ---
    def emit_log(self, type, message, user=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "type": type,
            "time": timestamp,
            "message": message,
            "user": user
        }
        if type == 'chat':
            logging.info(f"[CHAT] {user}: {message}")
        else:
            logging.info(f"[SYSTEM] {message}")
            
        if self.socketio:
            self.socketio.emit('new_log', log_entry)

    def emit_stats(self):
        if self.socketio:
            self.socketio.emit('stats_update', self.stats)

    # --- LOGIC ---
    def on_obs_event(self, event):
        if event.event_type == "MediaInputPlaybackEnded":
            if self.auto_return_timer:
                self.auto_return_timer.cancel()
                self.auto_return_timer = None
            
            try:
                current_scene = self.obs.get_current_scene()
                if current_scene in self.video_scenes:
                    msg = f"✓ Video ended in '{current_scene}'. Returning to '{self.main_scene_name}'."
                    self.emit_log('system', msg)
                    self.obs.switch_to_scene(self.main_scene_name)
            except Exception as e:
                logging.error(f"Error in on_obs_event: {e}")

    async def process_comment(self, user, comment):
        self.emit_log('chat', comment, user)
        self.stats['comments_processed'] += 1
        self.emit_stats()
        
        if not self.ai:
            return

        result = None
        if comment in self.processed_cache:
            result = self.processed_cache[comment]
        else:
            result = self.ai.analyze_comment(comment, self.product_list)
            if result.get('intent') != 'other' or result.get('product_name'):
                self.processed_cache[comment] = result

        if result.get('intent') == 'product_request':
            self._handle_product_request(result.get('product_name'))
        elif result.get('intent') == 'error':
            self.stats['errors'] += 1
            self.emit_stats()
    
    def _handle_product_request(self, product_name):
        if not product_name: return

        best_match = None
        highest_score = 0
        for official_name in self.product_list:
            score = SequenceMatcher(None, product_name.lower(), official_name.lower()).ratio()
            if score > highest_score:
                highest_score = score
                best_match = official_name
        
        if highest_score < 0.5 or not best_match:
            return

        now = time.time()
        self.rate_limit_timestamps = [t for t in self.rate_limit_timestamps if now - t < 60]
        
        if len(self.rate_limit_timestamps) < self.rate_limit:
            scene = self.product_to_scene_map.get(best_match)
            if scene:
                self.emit_log('system', f"AI detected intent for '{best_match}'. Switching to '{scene}'.")
                
                if self.obs.switch_to_scene(scene):
                    self.stats['scenes_switched'] += 1
                    self.rate_limit_timestamps.append(now)
                    self.emit_stats()
                    
                    if self.auto_return_timer: self.auto_return_timer.cancel()
                    self.auto_return_timer = threading.Timer(self.auto_return_delay, self._backup_return_to_main)
                    self.auto_return_timer.daemon = True
                    self.auto_return_timer.start()
                    self.emit_log('system', f"⏱️ Backup auto-return set for {self.auto_return_delay}s")
        else:
            self.emit_log('system', f"Rate limit hit. Ignoring request for '{best_match}'.")
    
    def _backup_return_to_main(self):
        try:
            current_scene = self.obs.get_current_scene()
            if current_scene in self.video_scenes:
                self.emit_log('system', f"⚠️ Backup timer: Returning to '{self.main_scene_name}'")
                self.obs.switch_to_scene(self.main_scene_name)
        except Exception as e:
            logging.error(f"Error in backup return: {e}")

    def _run_tiktok_listener(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        retry_count = 0
        
        while not self.stop_event.is_set():
            try:
                self.current_listener = TikTokListener(self.tiktok_username, self.process_comment)
                self.emit_log('system', f"Connecting to TikTok user: {self.tiktok_username}")
                self.current_listener.run() 
                
                # If run() returns, it usually means we disconnected
                retry_count = 0 
                
            except Exception as e:
                # IMPORTANT: If we are stopping, ignore the error and break
                if self.stop_event.is_set():
                    break
                    
                self.emit_log('system', f"Connection Error: {e}")
                self.stats['errors'] += 1
                self.emit_stats()
            finally:
                if self.current_listener:
                    try: self.current_listener.stop()
                    except: pass
                self.current_listener = None

            # IMPORTANT: Check stop event BEFORE waiting to reconnect
            if self.stop_event.is_set():
                break

            retry_count += 1
            wait_time = 5 if retry_count <= 2 else self.reconnect_delay
            self.emit_log('system', f"Disconnected. Retrying in {wait_time}s...")
            
            # Sleep in small chunks to allow faster stopping
            for _ in range(wait_time):
                if self.stop_event.is_set(): break
                time.sleep(1)
        
        loop.close()

    def start(self):
        if not self.obs.connect(): 
            self.emit_log('system', "Failed to connect to OBS WebSocket. Check settings.")
            return False
        
        self.emit_log('system', "Bot starting...")
        self.stop_event.clear()
        
        self.thread = threading.Thread(target=self._run_tiktok_listener, daemon=True)
        self.thread.start()
        
        return True

    def stop(self):
        self.emit_log('system', "Stopping bot...")
        self.stop_event.set() # 1. Signal threads to stop
        
        if self.auto_return_timer:
            self.auto_return_timer.cancel()
        
        # 2. Force TikTok client to stop if it exists
        if self.current_listener:
            try: 
                # This breaks the blocking .run() loop
                self.current_listener.client.stop() 
            except Exception as e: 
                logging.error(f"Error forcing TikTok stop: {e}")
        
        self.obs.disconnect()
        self.emit_log('system', "Bot stopped successfully.")