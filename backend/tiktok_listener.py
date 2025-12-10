# backend/tiktok_listener.py

from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
import logging
import warnings

# Suppress asyncio warnings during shutdown
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TikTokListener:
    """Connects to a TikTok Live stream and listens for comments."""

    def __init__(self, tiktok_username: str, on_comment_callback=None):
        """Initializes the listener for a specific TikTok user."""
        if not tiktok_username.startswith("@"):
            tiktok_username = "@" + tiktok_username
        
        self.client: TikTokLiveClient = TikTokLiveClient(unique_id=tiktok_username)
        self.on_comment_callback = on_comment_callback
        self._is_stopping = False
        self._setup_listeners()

    def _setup_listeners(self):
        """Attach event listeners to the client."""
        self.client.add_listener(ConnectEvent, self.on_connect)
        self.client.add_listener(CommentEvent, self.on_comment)
        self.client.add_listener(DisconnectEvent, self.on_disconnect)

    def run(self):
        """Start the connection and run the listener until stopped."""
        try:
            logging.info(f"Attempting to connect to {self.client.unique_id}'s live stream...")
            self.client.run()
        except Exception as e:
            # Suppress expected shutdown errors
            error_msg = str(e).lower()
            if self._is_stopping or "cancelled" in error_msg or "stop" in error_msg:
                logging.info("TikTok client stopped gracefully.")
            elif "different loop" in error_msg or "wasn't used" in error_msg:
                # Suppress async cleanup errors - these are harmless
                pass
            else:
                logging.error(f"TikTok connection error: {e}")
                raise
    
    def stop(self):
        """Explicitly stops the client and cleans up resources."""
        if self._is_stopping:
            return
            
        self._is_stopping = True
        logging.info("Stopping TikTok client...")
        
        try:
            if self.client and self.client.connected:
                # Just mark as disconnected - the run() loop will handle cleanup
                self.client._ws_closed = True
                logging.info("TikTok client marked for disconnection.")
            else:
                logging.info("TikTok client already disconnected.")
        except Exception as e:
            # Suppress common disconnect errors - they're expected during shutdown
            if "different loop" not in str(e) and "wasn't used" not in str(e):
                logging.error(f"Error during TikTok disconnect: {e}")
        finally:
            self._is_stopping = False

    async def on_connect(self, event: ConnectEvent):
        """Callback for when the client connects to the stream."""
        logging.info(f"✓ Successfully connected to {self.client.unique_id}!")

    async def on_disconnect(self, event: DisconnectEvent):
        """Callback for when the client disconnects from the stream."""
        logging.info(f"Disconnected from {self.client.unique_id}'s stream.")

    async def on_comment(self, event: CommentEvent):
        """Callback for when a new comment is received."""
        if self._is_stopping:
            return
            
        user_data = event.user_info
        if user_data and self.on_comment_callback:
            nickname = getattr(user_data, 'nick_name', "Unknown")
            await self.on_comment_callback(nickname, event.comment)