from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
import logging
import warnings
import asyncio

# Suppress annoying asyncio warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TikTokListener:
    """Connects to a TikTok Live stream and listens for comments."""

    def __init__(self, tiktok_username: str, on_comment_callback=None):
        if not tiktok_username.startswith("@"):
            tiktok_username = "@" + tiktok_username
        
        self.client: TikTokLiveClient = TikTokLiveClient(unique_id=tiktok_username)
        self.on_comment_callback = on_comment_callback
        self._is_stopping = False
        self._setup_listeners()

    def _setup_listeners(self):
        self.client.add_listener(ConnectEvent, self.on_connect)
        self.client.add_listener(CommentEvent, self.on_comment)
        self.client.add_listener(DisconnectEvent, self.on_disconnect)

    def run(self):
        try:
            logging.info(f"Connecting to {self.client.unique_id}...")
            self.client.run()
        except Exception as e:
            # Cleanly handle expected stop errors
            if self._is_stopping: return
            error_msg = str(e).lower()
            if "cancelled" in error_msg or "stop" in error_msg: return
            logging.error(f"TikTok Listener Error: {e}")
            raise
    
    def stop(self):
        self._is_stopping = True
        try:
            if self.client and self.client.connected:
                self.client._ws_closed = True
        except: pass

    async def on_connect(self, event: ConnectEvent):
        logging.info(f"Connected to {self.client.unique_id}!")

    async def on_disconnect(self, event: DisconnectEvent):
        logging.info(f"Disconnected from stream.")

    async def on_comment(self, event: CommentEvent):
        if self._is_stopping: return
        user_data = event.user_info
        if user_data and self.on_comment_callback:
            nickname = getattr(user_data, 'nick_name', "Unknown")
            await self.on_comment_callback(nickname, event.comment)