# backend/engine.py

import logging
import os
import time
import json
from pathlib import Path
import threading
import asyncio
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import defaultdict

from obs_controller import OBSController
from ai_processor import AIProcessor
from tiktok_listener import TikTokListener

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def load_configuration():
    """Loads the entire configuration from the central config.json file."""
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # Validate configuration
        required_fields = ['tiktok_username', 'deepseek_api_key', 'product_list', 'product_to_scene_map']
        for field in required_fields:
            if field not in config:
                logging.error(f"FATAL: Missing required field '{field}' in config.json")
                return None
        
        # Validate product list matches scene map
        products = set(config['product_list'])
        mapped_products = set(config['product_to_scene_map'].keys())
        if products != mapped_products:
            logging.error(f"FATAL: Product list and scene map don't match!")
            logging.error(f"Products: {products}")
            logging.error(f"Mapped: {mapped_products}")
            return None
            
        return config
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"FATAL: Could not load or parse config.json. Error: {e}")
        return None


def find_best_product_match(ai_product_name: str, official_product_list: list[str]) -> str | None:
    """
    Enhanced fuzzy matching with string similarity for typo handling.
    
    Args:
        ai_product_name: The (potentially messy) product name from the AI.
        official_product_list: The list of exact product names from the config.
    
    Returns:
        The official product name if a good match is found, otherwise None.
    """
    if not ai_product_name or not official_product_list:
        return None
    
    ai_lower = ai_product_name.lower()
    best_match = None
    highest_score = 0
    
    for official_name in official_product_list:
        official_lower = official_name.lower()
        
        # Method 1: Exact substring match
        if ai_lower in official_lower or official_lower in ai_lower:
            score = 0.9
        else:
            # Method 2: Word overlap
            ai_words = set(ai_lower.split())
            official_words = set(official_lower.split())
            matching_words = ai_words.intersection(official_words)
            word_score = len(matching_words) / max(len(ai_words), len(official_words))
            
            # Method 3: String similarity (handles typos)
            similarity_score = SequenceMatcher(None, ai_lower, official_lower).ratio()
            
            # Combine scores
            score = max(word_score, similarity_score)
        
        if score > highest_score:
            highest_score = score
            best_match = official_name
    
    # Accept match if score is above threshold
    if highest_score >= 0.5:  # 50% similarity threshold
        logging.info(f"Fuzzy match: '{ai_product_name}' -> '{best_match}' (score: {highest_score:.2f})")
        return best_match
    
    logging.warning(f"No confident match for '{ai_product_name}' (best score: {highest_score:.2f})")
    return None


class CommentCache:
    """Simple cache to avoid re-processing similar comments."""
    
    def __init__(self, duration_seconds=300):
        self.cache = {}
        self.duration = timedelta(seconds=duration_seconds)
    
    def get(self, comment: str):
        """Get cached result if still valid."""
        comment_lower = comment.lower().strip()
        if comment_lower in self.cache:
            result, timestamp = self.cache[comment_lower]
            if datetime.now() - timestamp < self.duration:
                return result
            else:
                del self.cache[comment_lower]
        return None
    
    def set(self, comment: str, result: dict):
        """Store result in cache."""
        comment_lower = comment.lower().strip()
        self.cache[comment_lower] = (result, datetime.now())
    
    def clear(self):
        """Clear all cached results."""
        self.cache.clear()


class RateLimiter:
    """Rate limiter to prevent excessive scene switches."""
    
    def __init__(self, max_per_minute=2):
        self.max_per_minute = max_per_minute
        self.events = []
    
    def can_proceed(self) -> bool:
        """Check if action is allowed under rate limit."""
        now = datetime.now()
        # Remove events older than 1 minute
        self.events = [t for t in self.events if now - t < timedelta(minutes=1)]
        
        if len(self.events) < self.max_per_minute:
            self.events.append(now)
            return True
        return False


class MainApplication:
    """The main class that orchestrates all components."""
    
    def __init__(self):
        config = load_configuration()
        if not config:
            raise ValueError("Failed to start due to configuration error. Check logs.")
        
        # Load configuration
        self.tiktok_username = config.get("tiktok_username")
        self.product_list = config.get("product_list", [])
        self.product_to_scene_map = config.get("product_to_scene_map", {})
        self.main_scene_name = config.get("main_scene_name", "Scene_A")
        self.reconnect_delay = config.get("tiktok_reconnect_delay", 30)
        
        deepseek_api_key = config.get("deepseek_api_key")
        obs_host = config.get("obs_ws_host", "localhost")
        obs_port = config.get("obs_ws_port", 4455)
        obs_password = config.get("obs_ws_password", "")
        
        if not deepseek_api_key:
            raise ValueError("deepseek_api_key not found in config.json.")
        
        # Initialize components with full configuration
        self.obs = OBSController(
            host=obs_host,
            port=obs_port,
            password=obs_password,
            event_callback=self.on_obs_event
        )
        self.ai = AIProcessor(api_key=deepseek_api_key)
        
        # Initialize cache and rate limiter
        cache_duration = config.get("cache_duration_seconds", 300)
        rate_limit = config.get("comment_rate_limit", 2)
        self.cache = CommentCache(duration_seconds=cache_duration)
        self.rate_limiter = RateLimiter(max_per_minute=rate_limit)
        
        # Threading setup
        self.loop = asyncio.new_event_loop()
        self.stop_event = threading.Event()
        self.video_scenes = {scene for scene in self.product_to_scene_map.values() 
                           if scene != self.main_scene_name}
        
        # Statistics
        self.stats = {
            'comments_processed': 0,
            'scenes_switched': 0,
            'cache_hits': 0,
            'rate_limited': 0,
            'errors': 0
        }
    
    def on_obs_event(self, event):
        """Callback for OBS events - returns to main scene when video ends."""
        try:
            if event.event_type == "MediaInputPlaybackEnded":
                source_name = event.event_data.get("inputName", "Unknown")
                logging.info(f"[OBS EVENT] Media source '{source_name}' finished playing.")
                
                # Get current scene
                current_scene_name = self.obs.get_current_scene()
                
                if current_scene_name:
                    logging.info(f"[OBS EVENT] Current scene is: '{current_scene_name}'")
                    
                    # Check if we're in a product scene
                    if current_scene_name in self.video_scenes:
                        logging.info(f"[ACTION] Product video ended in '{current_scene_name}'. "
                                   f"Returning to main scene '{self.main_scene_name}'.")
                        self.obs.switch_to_scene(self.main_scene_name)
                    else:
                        logging.info(f"[SKIPPED] Media ended but we're not in a product scene.")
                else:
                    logging.warning("[OBS EVENT] Could not determine current scene")
        except Exception as e:
            logging.error(f"Error in on_obs_event: {e}")
            self.stats['errors'] += 1
    
    async def process_comment(self, user: str, comment: str):
        """This method is called by TikTokListener for each new comment."""
        logging.info(f"[COMMENT] {user}: '{comment}'")
        self.stats['comments_processed'] += 1
        
        # Check cache first
        cached_result = self.cache.get(comment)
        if cached_result:
            logging.info(f"[CACHE HIT] Using cached result for similar comment")
            self.stats['cache_hits'] += 1
            ai_result = cached_result
        else:
            # Call AI for analysis
            ai_result = self.ai.analyze_comment(comment, self.product_list)
            
            # Cache the result
            if ai_result and ai_result.get('intent') != 'error':
                self.cache.set(comment, ai_result)
        
        if ai_result and ai_result.get('intent') == 'product_request':
            messy_product_name = ai_result.get('product_name')
            
            if messy_product_name:
                # Find the official product name using enhanced fuzzy matching
                official_product_name = find_best_product_match(messy_product_name, self.product_list)
                
                if official_product_name:
                    # Check rate limit
                    if not self.rate_limiter.can_proceed():
                        logging.warning(f"[RATE LIMITED] Too many scene switches. Ignoring request.")
                        self.stats['rate_limited'] += 1
                        return
                    
                    target_scene = self.product_to_scene_map.get(official_product_name)
                    if target_scene:
                        logging.info(f"[ACTION] Switching to scene '{target_scene}' for '{official_product_name}'")
                        self.obs.switch_to_scene(target_scene)
                        self.stats['scenes_switched'] += 1
                    else:
                        logging.warning(f"[SKIPPED] Product '{official_product_name}' not in scene map.")
        elif ai_result and ai_result.get('intent') == 'error':
            self.stats['errors'] += 1
    
    def run_tiktok_listener_in_thread(self):
        """Runs the TikTok listener in a background thread with auto-reconnect."""
        asyncio.set_event_loop(self.loop)
        
        while not self.stop_event.is_set():
            try:
                listener = TikTokListener(
                    tiktok_username=self.tiktok_username,
                    on_comment_callback=self.process_comment
                )
                logging.info(f"Connecting to TikTok user: {self.tiktok_username}")
                listener.run()
            except Exception as e:
                if not self.stop_event.is_set():
                    logging.error(f"Exception in listener thread: {e}")
                    self.stats['errors'] += 1
            
            if not self.stop_event.is_set():
                logging.warning(f"Listener disconnected. Reconnecting in {self.reconnect_delay} seconds...")
                for _ in range(self.reconnect_delay):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        
        logging.info("TikTok listener thread has stopped.")
    
    def start(self):
        """Starts the application."""
        logging.info("=" * 60)
        logging.info("Starting AI Scene Changer Application")
        logging.info("=" * 60)
        
        if not self.obs.connect():
            logging.error("Could not connect to OBS. The application will not start.")
            return
        
        logging.info(f"Main scene: {self.main_scene_name}")
        logging.info(f"Products: {', '.join(self.product_list)}")
        logging.info(f"Rate limit: {self.rate_limiter.max_per_minute} switches per minute")
        logging.info(f"Cache duration: {self.cache.duration.total_seconds()} seconds")
        
        logging.info("Starting TikTok listener in background thread...")
        listener_thread = threading.Thread(target=self.run_tiktok_listener_in_thread, daemon=True)
        listener_thread.start()
        
        print("\n" + "=" * 60)
        print(">>> Application is RUNNING! Press Ctrl+C to stop. <<<")
        print("=" * 60 + "\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\nCtrl+C detected. Shutting down gracefully...")
        finally:
            self.stop()
    
    def stop(self):
        """Stops the application gracefully."""
        logging.info("Initiating shutdown sequence...")
        self.stop_event.set()
        time.sleep(2)  # Give threads time to finish
        self.obs.disconnect()
        
        # Print statistics
        logging.info("=" * 60)
        logging.info("Session Statistics:")
        logging.info(f"  Comments processed: {self.stats['comments_processed']}")
        logging.info(f"  Scenes switched: {self.stats['scenes_switched']}")
        logging.info(f"  Cache hits: {self.stats['cache_hits']}")
        logging.info(f"  Rate limited: {self.stats['rate_limited']}")
        logging.info(f"  Errors: {self.stats['errors']}")
        logging.info("=" * 60)
        logging.info("Application has been shut down.")
    
    def get_stats(self):
        """Returns current statistics."""
        return self.stats.copy()


if __name__ == '__main__':
    app = MainApplication()
    app.start()