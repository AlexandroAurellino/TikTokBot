# backend/engine.py

import logging
import time
import threading
import asyncio
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import deque

from obs_controller import OBSController
from ai_processor import AIProcessor
from tiktok_listener import TikTokListener
import database 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class CommentCache:
    """Simple cache to avoid re-processing similar comments."""
    def __init__(self, duration_seconds=300):
        self.cache = {}
        self.duration = timedelta(seconds=duration_seconds)
    
    def get(self, comment):
        comment_lower = comment.lower().strip()
        if comment_lower in self.cache:
            result, timestamp = self.cache[comment_lower]
            if datetime.now() - timestamp < self.duration:
                return result
            else:
                del self.cache[comment_lower]
        return None
    
    def set(self, comment, result):
        self.cache[comment.lower().strip()] = (result, datetime.now())
    
    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()


class RateLimiter:
    """Rate limiter to prevent excessive scene switches."""
    def __init__(self, max_per_minute=2):
        self.max_per_minute = max_per_minute
        self.events = []
    
    def can_proceed(self):
        now = datetime.now()
        self.events = [t for t in self.events if now - t < timedelta(minutes=1)]
        
        if len(self.events) < self.max_per_minute:
            self.events.append(now)
            return True
        return False
    
    def reset(self):
        """Reset the rate limiter."""
        self.events.clear()


def find_best_product_match(ai_product_name, official_product_list):
    """Fuzzy matching to find the best product match."""
    if not ai_product_name or not official_product_list: 
        return None
        
    ai_lower = ai_product_name.lower()
    best_match = None
    highest_score = 0
    
    for official_name in official_product_list:
        official_lower = official_name.lower()
        if ai_lower in official_lower or official_lower in ai_lower: 
            score = 0.9
        else:
            score = SequenceMatcher(None, ai_lower, official_lower).ratio()
        
        if score > highest_score:
            highest_score = score
            best_match = official_name
            
    return best_match if highest_score >= 0.5 else None


class MainApplication:
    """The main application orchestrating all components."""
    
    def __init__(self):
        self.config = database.load_settings()
        self._init_settings()
        self._init_components()
        self._init_state()
        
    def _init_settings(self):
        """Extract and validate settings from config."""
        self.tiktok_username = self.config.get("tiktok_username")
        self.product_list = self.config.get("product_list", [])
        self.product_to_scene_map = self.config.get("product_to_scene_map", {})
        self.main_scene_name = self.config.get("main_scene_name", "Scene_A")
        
        self.reconnect_delay = int(self.config.get("tiktok_reconnect_delay", 30))
        rate_limit = int(self.config.get("comment_rate_limit", 2))
        cache_duration = int(self.config.get("cache_duration_seconds", 300))
        obs_port = int(self.config.get("obs_ws_port", 4455))
        
        self.deepseek_api_key = self.config.get("deepseek_api_key")
        self.obs_host = self.config.get("obs_ws_host", "localhost")
        self.obs_password = self.config.get("obs_ws_password", "")
        
        if not self.deepseek_api_key:
            raise ValueError("deepseek_api_key not found in settings.")
        
        self.rate_limit = rate_limit
        self.cache_duration = cache_duration
        self.obs_port = obs_port
    
    def _init_components(self):
        """Initialize OBS, AI, and supporting components."""
        self.obs = OBSController(
            host=self.obs_host,
            port=self.obs_port,
            password=self.obs_password,
            event_callback=self.on_obs_event
        )
        
        self.ai = AIProcessor(api_key=self.deepseek_api_key)
        self.cache = CommentCache(duration_seconds=self.cache_duration)
        self.rate_limiter = RateLimiter(max_per_minute=self.rate_limit)
        
        self.video_scenes = {
            scene for scene in self.product_to_scene_map.values() 
            if scene != self.main_scene_name
        }
    
    def _init_state(self):
        """Initialize application state variables."""
        self.loop = None
        self.thread = None
        self.stop_event = threading.Event()
        self.current_listener = None
        
        # Scene tracking for auto-return
        self.last_scene_switch_time = None
        self.auto_return_timer = None
        self.auto_return_delay = 30  # seconds - fallback if video end event doesn't fire
        
        self.stats = {
            'comments_processed': 0,
            'scenes_switched': 0, 
            'cache_hits': 0,
            'rate_limited': 0,
            'errors': 0
        }
        self.logs = deque(maxlen=50)
    
    def add_log(self, type, message, user=None):
        """Add a log entry for UI and console."""
        entry = {
            "type": type,
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "user": user
        }
        self.logs.append(entry)
        
        if type == 'chat':
            logging.info(f"[CHAT] {user}: {message}")
        else:
            logging.info(f"[SYSTEM] {message}")

    def on_obs_event(self, event):
        """Callback for OBS media playback events."""
        if event.event_type == "MediaInputPlaybackEnded":
            try:
                # Cancel backup timer since video ended naturally
                if self.auto_return_timer:
                    self.auto_return_timer.cancel()
                    self.auto_return_timer = None
                
                current_scene = self.obs.get_current_scene()
                if current_scene in self.video_scenes:
                    msg = f"✓ Video ended in '{current_scene}'. Returning to '{self.main_scene_name}'."
                    self.add_log('system', msg)
                    self.obs.switch_to_scene(self.main_scene_name)
                else:
                    logging.debug(f"Video ended in '{current_scene}' but it's not a product scene.")
            except Exception as e:
                logging.error(f"Error in on_obs_event: {e}")

    async def process_comment(self, user, comment):
        """Process a single comment through AI and handle product requests."""
        self.add_log('chat', comment, user)
        self.stats['comments_processed'] += 1
        
        # Check cache first
        cached_result = self.cache.get(comment)
        if cached_result:
            self.stats['cache_hits'] += 1
            ai_result = cached_result
        else:
            # Analyze with AI
            ai_result = self.ai.analyze_comment(comment, self.product_list)
            if ai_result.get('intent') != 'error':
                self.cache.set(comment, ai_result)

        # Handle product requests
        if ai_result.get('intent') == 'product_request':
            self._handle_product_request(ai_result.get('product_name'))
        elif ai_result.get('intent') == 'error':
            self.stats['errors'] += 1
    
    def _handle_product_request(self, product_name):
        """Handle a product request with rate limiting and scene switching."""
        product = find_best_product_match(product_name, self.product_list)
        
        if not product:
            return
            
        if self.rate_limiter.can_proceed():
            scene = self.product_to_scene_map.get(product)
            if scene:
                self.add_log('system', f"AI detected intent for '{product}'. Switching to '{scene}'.")
                success = self.obs.switch_to_scene(scene)
                
                if success:
                    self.stats['scenes_switched'] += 1
                    self.last_scene_switch_time = datetime.now()
                    
                    # Start backup timer in case MediaInputPlaybackEnded doesn't fire
                    if self.auto_return_timer:
                        self.auto_return_timer.cancel()
                    
                    self.auto_return_timer = threading.Timer(
                        self.auto_return_delay,
                        self._backup_return_to_main
                    )
                    self.auto_return_timer.daemon = True
                    self.auto_return_timer.start()
                    
                    self.add_log('system', f"⏱️ Backup auto-return set for {self.auto_return_delay}s")
        else:
            self.stats['rate_limited'] += 1
            self.add_log('system', f"Rate limit hit. Ignoring request for '{product}'.")
    
    def _backup_return_to_main(self):
        """Backup method to return to main scene if video end event doesn't fire."""
        try:
            current_scene = self.obs.get_current_scene()
            if current_scene in self.video_scenes:
                self.add_log('system', f"⚠️ Backup timer: Returning to '{self.main_scene_name}' from '{current_scene}'")
                self.add_log('system', "💡 TIP: Check that 'Loop' is UNCHECKED on your media source!")
                self.obs.switch_to_scene(self.main_scene_name)
        except Exception as e:
            logging.error(f"Error in backup return: {e}")
    
    def _asyncio_exception_handler(self, loop, context):
        """Custom exception handler to suppress expected shutdown errors."""
        exception = context.get('exception')
        if exception:
            error_msg = str(exception).lower()
            # Suppress expected shutdown errors
            if 'different loop' in error_msg or "wasn't used" in error_msg:
                return
        # Log other exceptions normally
        logging.error(f"Asyncio exception: {context['message']}")
        if exception:
            logging.error(f"Exception: {exception}")

    def _run_tiktok_listener(self):
        """Run TikTok listener with retry logic in dedicated event loop."""
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Suppress annoying asyncio error messages during shutdown
        self.loop.set_exception_handler(self._asyncio_exception_handler)
        
        retry_count = 0
        
        while not self.stop_event.is_set():
            try:
                self.current_listener = TikTokListener(
                    self.tiktok_username, 
                    self.process_comment
                )
                self.add_log('system', f"Connecting to TikTok user: {self.tiktok_username}")
                
                # This blocks until disconnected
                self.current_listener.run()
                
                # Reset retry count on successful connection
                retry_count = 0
                
            except Exception as e:
                self.add_log('system', f"Connection Error: {e}")
                self.stats['errors'] += 1
            finally:
                # Clean up listener reference
                if self.current_listener:
                    try:
                        self.current_listener.stop()
                    except:
                        pass
                self.current_listener = None

            # Handle reconnection with fast retry
            if not self.stop_event.is_set():
                retry_count += 1
                wait_time = 5 if retry_count <= 2 else self.reconnect_delay
                
                self.add_log('system', f"Disconnected. Attempt {retry_count}. Retrying in {wait_time}s...")
                
                # Sleep in small chunks to allow interruption
                for _ in range(wait_time):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        
        # Clean up event loop
        try:
            self.loop.close()
        except:
            pass
        self.loop = None

    def start(self):
        """Start the application."""
        if not self.obs.connect(): 
            self.add_log('system', "Failed to connect to OBS WebSocket. Check settings.")
            return False
        
        self.add_log('system', "Bot starting...")
        self.stop_event.clear()
        
        # Start TikTok listener in separate thread
        self.thread = threading.Thread(target=self._run_tiktok_listener, daemon=True)
        self.thread.start()
        
        return True

    def stop(self):
        """Stop the application gracefully."""
        self.add_log('system', "Stopping bot...")
        
        # Signal stop
        self.stop_event.set()
        
        # Cancel any pending auto-return timer
        if self.auto_return_timer:
            self.auto_return_timer.cancel()
            self.auto_return_timer = None
        
        # Stop TikTok listener
        if self.current_listener:
            try:
                self.current_listener.stop()
            except Exception as e:
                logging.error(f"Error stopping TikTok listener: {e}")
        
        # Wait for thread to finish (with timeout)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        # Disconnect OBS
        self.obs.disconnect()
        
        # Clear caches and reset rate limiter
        self.cache.clear()
        self.rate_limiter.reset()
        
        self.add_log('system', "Bot stopped successfully.")
    
    def get_data(self):
        """Return current stats and logs for frontend."""
        return {
            "stats": self.stats.copy(),
            "logs": list(self.logs)
        }


if __name__ == '__main__':
    try:
        app = MainApplication()
        if app.start():
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        app.stop()
    except Exception as e:
        print(f"Error starting app: {e}")