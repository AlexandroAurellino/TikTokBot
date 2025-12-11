import logging
import time
import threading
import asyncio
import os
from datetime import datetime
from difflib import SequenceMatcher
from collections import deque

# Relative imports
from .obs import OBSController
from .ai import AIProcessor
from .tiktok import TikTokListener
from . import database 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MainApplication:
    def __init__(self, socketio_instance=None, upload_folder=None):
        self.socketio = socketio_instance 
        self.upload_folder = upload_folder
        self.config = database.load_settings()
        self._init_settings()
        
        self.obs = OBSController(
            host=self.obs_host,
            port=self.obs_port,
            password=self.obs_password,
            event_callback=self.on_obs_event
        )
        
        self.ai = AIProcessor(api_key=self.deepseek_api_key) if self.deepseek_api_key else None
        
        self.stop_event = threading.Event()
        self.thread = None
        self.current_listener = None
        
        # --- PLAYBACK STATE ---
        self.request_queue = deque() # The line of products waiting to be shown
        self.is_playing = False      # Is a video currently running?
        self.auto_return_timer = None
        self.auto_return_delay = 30  # Safety buffer (video length + buffer)
        
        self.processed_cache = {} 
        self.rate_limit_timestamps = [] 
        
        self.stats = {'comments_processed': 0, 'scenes_switched': 0, 'errors': 0}
        self.current_product_name = None # NEW: Track what is playing
        
    def _init_settings(self):
        self.tiktok_username = self.config.get("tiktok_username")
        
        # Store FULL product data
        self.products_data = self.config.get('products', []) 
        self.product_names_list = [p['name'] for p in self.products_data]
        self.product_to_video_map = {p['name']: p['scene'] for p in self.products_data}
        
        self.main_scene_name = self.config.get("main_scene_name", "Scene_A")
        self.product_scene_name = "Product_View"
        self.media_source_name = "Dynamic_Media"
        
        self.reconnect_delay = int(self.config.get("tiktok_reconnect_delay", 30))
        self.deepseek_api_key = self.config.get("deepseek_api_key")
        self.obs_host = self.config.get("obs_ws_host", "localhost")
        self.obs_port = int(self.config.get("obs_ws_port", 4455))
        self.obs_password = self.config.get("obs_ws_password", "")
        self.rate_limit = int(self.config.get("comment_rate_limit", 2))

    def emit_log(self, type, message, user=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if type == 'chat': logging.info(f"[CHAT] {user}: {message}")
        else: logging.info(f"[SYSTEM] {message}")  
        if self.socketio:
            self.socketio.emit('new_log', {"type": type, "time": timestamp, "message": message, "user": user})

    def emit_stats(self):
        # Include Queue and Current Video in the update
        stats_packet = {
            **self.stats,
            'current_product': self.current_product_name,
            'queue': list(self.request_queue)
        }
        if self.socketio: 
            self.socketio.emit('stats_update', stats_packet)

    # --- CORE EVENT LOGIC ---

    def on_obs_event(self, event):
        """Called when OBS finishes playing a video."""
        if event.event_type == "MediaInputPlaybackEnded":
            # Cancel the safety timer because the video finished naturally
            if self.auto_return_timer:
                self.auto_return_timer.cancel()
                self.auto_return_timer = None
            
            try:
                # Only react if we are actually in the product scene
                if self.obs.get_current_scene() == self.product_scene_name:
                    self._play_next_or_return()
            except Exception as e:
                logging.error(f"OBS Event Error: {e}")

    def _play_next_or_return(self):
        """Decides whether to play the next queued item or go to main scene."""
        if self.request_queue:
            # 1. Queue has items? Play next.
            next_product = self.request_queue.popleft()
            self.emit_log('system', f"Queue: Playing next item '{next_product}'")
            self._play_video_for_product(next_product)
        else:
            # 2. Queue empty? Go home.
            self.is_playing = False
            self.current_product_name = None # Reset
            self.emit_log('system', f"Queue empty. Returning to '{self.main_scene_name}'")
            self.obs.switch_to_scene(self.main_scene_name)
            self.emit_stats() # Update UI

    async def process_comment(self, user, comment):
        self.emit_log('chat', comment, user)
        self.stats['comments_processed'] += 1
        self.emit_stats()
        
        if not self.ai: return

        # Check Cache
        result = self.processed_cache.get(comment)
        if not result:
            result = self.ai.analyze_comment(comment, self.products_data)
            if result.get('intent') != 'other' or result.get('product_name'):
                self.processed_cache[comment] = result

        if result.get('intent') == 'product_request':
            self._handle_product_request(result.get('product_name'))

    def _handle_product_request(self, product_name):
        if not product_name: return

        # 1. Fuzzy Match
        best_match = None
        highest_score = 0
        for official_name in self.product_names_list:
            score = SequenceMatcher(None, product_name.lower(), official_name.lower()).ratio()
            if score > highest_score:
                highest_score = score
                best_match = official_name
        
        if highest_score < 0.5 or not best_match: return

        # 2. Rate Limit Check
        now = time.time()
        self.rate_limit_timestamps = [t for t in self.rate_limit_timestamps if now - t < 60]
        
        if len(self.rate_limit_timestamps) < self.rate_limit:
            self.rate_limit_timestamps.append(now)
            
            # 3. Queue Logic
            if self.is_playing:
                # Video is currently playing
                if best_match in self.request_queue:
                    self.emit_log('system', f"'{best_match}' is already in queue. Skipping.")
                else:
                    self.request_queue.append(best_match)
                    self.emit_log('system', f"Video playing. Added '{best_match}' to queue (Position: {len(self.request_queue)})")
            else:
                # Nothing playing, play immediately
                self._play_video_for_product(best_match)
        else:
            self.emit_log('system', f"Rate limit hit. Ignoring '{best_match}'")

    def _play_video_for_product(self, product_name):
        """Internal helper to actually switch OBS to the video."""
        video_filename = self.product_to_video_map.get(product_name)
        
        if video_filename:
            video_path = os.path.join(self.upload_folder, video_filename)
            self.emit_log('system', f"Loading Video: {video_filename}")
            
            # 1. Set File
            if self.obs.set_media_source_file(self.media_source_name, video_path):
                # 2. Switch Scene
                if self.obs.switch_to_scene(self.product_scene_name):
                    self.is_playing = True
                    self.current_product_name = product_name # Set current
                    self.stats['scenes_switched'] += 1
                    self.emit_stats()
                    
                    # 3. Set Backup Timer (Safety net if video event fails)
                    if self.auto_return_timer: self.auto_return_timer.cancel()
                    self.auto_return_timer = threading.Timer(self.auto_return_delay, self._backup_timeout)
                    self.auto_return_timer.daemon = True
                    self.auto_return_timer.start()
            else:
                self.emit_log('system', f"Failed to set media source. Check OBS.")
        else:
            self.emit_log('system', f"No video file found for '{product_name}'")

    def skip_current(self):
        """Forces the current video to stop and moves to the next."""
        if self.is_playing:
            self.emit_log('system', "⏭️ User pressed SKIP.")
            # We just call the logic that runs when a video ends
            self._play_next_or_return()
            return True
        return False
    
    def manual_play(self, product_name):
        """Allows the user to click a button to play a product."""
        self.emit_log('system', f"▶️ Manual trigger: {product_name}")
        self._handle_product_request(product_name)
        return True

    def _backup_timeout(self):
        """Called if the video plays for too long (safety timeout)."""
        try:
            if self.obs.get_current_scene() == self.product_scene_name:
                self.emit_log('system', "⚠️ Backup timer triggered (Video possibly stuck). Checking queue...")
                self._play_next_or_return()
        except: pass

    # --- TIKTOK CONNECTION ---

    def _run_tiktok_listener(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        retry_count = 0
        while not self.stop_event.is_set():
            try:
                self.current_listener = TikTokListener(self.tiktok_username, self.process_comment)
                self.emit_log('system', f"Connecting to {self.tiktok_username}...")
                self.current_listener.run()
                retry_count = 0
            except Exception as e:
                if self.stop_event.is_set(): break
                self.emit_log('system', f"Connection Error: {e}")
                self.stats['errors'] += 1
                self.emit_stats()
            finally:
                if self.current_listener:
                    try: self.current_listener.stop()
                    except: pass
                self.current_listener = None

            if self.stop_event.is_set(): break
            retry_count += 1
            wait_time = 5 if retry_count <= 2 else self.reconnect_delay
            self.emit_log('system', f"Retry in {wait_time}s...")
            for _ in range(wait_time):
                if self.stop_event.is_set(): break
                time.sleep(1)
        loop.close()

    def start(self):
        if not self.obs.connect(): 
            self.emit_log('system', "OBS Connection Failed")
            return False
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run_tiktok_listener, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.emit_log('system', "Stopping...")
        self.stop_event.set()
        if self.auto_return_timer: self.auto_return_timer.cancel()
        if self.current_listener:
            try: self.current_listener.client.stop()
            except: pass
        self.obs.disconnect()
        self.emit_log('system', "Stopped.")