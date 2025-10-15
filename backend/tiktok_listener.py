# backend/tiktok_listener.py

from TikTokLive import TikTokLiveClient
# THIS IS THE CORRECT IMPORT for modern versions of the library (v6.x and newer)
from TikTokLive.events import CommentEvent, ConnectEvent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TikTokListener:
    """Connects to a TikTok Live stream and listens for comments."""

    def __init__(self, tiktok_username: str, on_comment_callback=None):
        """Initializes the listener for a specific TikTok user."""
        # Ensure the username starts with @ for the library
        if not tiktok_username.startswith("@"):
            tiktok_username = "@" + tiktok_username
        
        # Instantiate the client
        self.client: TikTokLiveClient = TikTokLiveClient(unique_id=tiktok_username)

        # STORE the callback function
        self.on_comment_callback = on_comment_callback

        self._setup_listeners()

    def _setup_listeners(self):
        """A helper method to attach event listeners."""
        self.client.add_listener(ConnectEvent, self.on_connect)
        self.client.add_listener(CommentEvent, self.on_comment)

    def run(self):
        """Start the connection and run the listener until stopped."""
        try:
            logging.info(f"Attempting to connect to {self.client.unique_id}'s live stream...")
            self.client.run()
        except Exception as e:
            logging.error(f"Failed to connect or the stream ended: {e}")

    async def on_connect(self, event: ConnectEvent):
        """Callback for when the client connects to the stream."""
        logging.info(f"Successfully connected to the live stream for {self.client.unique_id}!")
        logging.info("Waiting for comments... (Press Ctrl+C to stop)")

    async def on_comment(self, event: CommentEvent):
        """Callback for when a new comment is received."""
        if event.user and self.on_comment_callback:
            await self.on_comment_callback(event.user.nickname, event.comment)

# --- Test block for running this file directly ---
# if __name__ == '__main__':
#     # IMPORTANT: Replace with the @username of a user who is CURRENTLY LIVE.
#     TIKTOK_USERNAME = "@queenofstyleid"

#     print("\n--- Starting TikTok Listener Test ---")
#     print(f"Make sure {TIKTOK_USERNAME} is currently live.")
    
#     try:
#         listener = TikTokListener(tiktok_username=TIKTOK_USERNAME)
#         listener.run()
#     except KeyboardInterrupt:
#         print("\nListener stopped by user.")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#     finally:
#         print("\n--- Listener Test Finished ---")