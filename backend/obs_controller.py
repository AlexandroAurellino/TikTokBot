import obsws_python as obs
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class OBSController:
    """A class to manage the connection and commands for OBS."""
    
    def __init__(self, host='localhost', port=4455, password='', event_callback=None):
        """Initializes the connection details."""
        self.host = host
        self.port = port
        self.password = password
        self.event_callback = event_callback
        
        # Initialize clients as None
        self.req_client = None
        self.event_client = None
    
    def connect(self):
        """Connects to the OBS WebSocket server."""
        try:
            # Create the request client
            self.req_client = obs.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password
            )
            
            # Test the connection
            version = self.req_client.get_version()
            logging.info(f"Successfully connected to OBS WebSocket v{version.obs_web_socket_version}")
            
            # Create separate event client if callback is provided
            if self.event_callback:
                self.event_client = obs.EventClient(
                    host=self.host,
                    port=self.port,
                    password=self.password
                )
                
                # Register the callback for media ended events
                self.event_client.callback.register(self._on_media_input_playback_ended)
                logging.info("Event client created and callback registered for MediaInputPlaybackEnded")
            
            return True
        except Exception as e:
            self.req_client = None
            self.event_client = None
            logging.error(f"Failed to connect to OBS WebSocket: {e}")
            logging.error("--> Is OBS running? Is the WebSocket Server enabled?")
            return False
    
    def _on_media_input_playback_ended(self, event_data):
        """Internal callback that gets triggered by OBS events."""
        try:
            logging.info(f"[OBS EVENT] Media playback ended: {event_data}")
            
            # Create a simple event object to pass to the user's callback
            class SimpleEvent:
                def __init__(self, event_type, data):
                    self.event_type = event_type
                    self.event_data = data
            
            # Call the user's callback if it exists
            if self.event_callback:
                event = SimpleEvent("MediaInputPlaybackEnded", event_data)
                self.event_callback(event)
        except Exception as e:
            logging.error(f"Error in media ended callback: {e}")
    
    def disconnect(self):
        """Disconnects from the OBS WebSocket server."""
        try:
            if self.event_client:
                self.event_client.disconnect()
                self.event_client = None
                logging.info("Disconnected event client from OBS WebSocket.")
            
            if self.req_client:
                self.req_client.disconnect()
                self.req_client = None
                logging.info("Disconnected request client from OBS WebSocket.")
        except Exception as e:
            logging.error(f"Error during disconnect: {e}")
    
    def switch_to_scene(self, scene_name: str):
        """Requests OBS to switch to a specific scene."""
        if not self.req_client:
            logging.warning("Not connected to OBS. Cannot switch scene.")
            return False
        
        try:
            scene_list_response = self.req_client.get_scene_list()
            if scene_list_response:
                available_scenes = [s['sceneName'] for s in scene_list_response.scenes]
                
                if scene_name in available_scenes:
                    self.req_client.set_current_program_scene(scene_name)
                    logging.info(f"✓ Successfully switched OBS scene to '{scene_name}'.")
                    return True
                else:
                    logging.warning(f"✗ Scene '{scene_name}' not found in OBS.")
                    logging.warning(f"Available scenes: {available_scenes}")
                    return False
            return False
        except Exception as e:
            logging.error(f"An error occurred while switching scenes: {e}")
            return False
    
    def get_current_scene(self):
        """Gets the current active scene name."""
        if not self.req_client:
            return None
        
        try:
            response = self.req_client.get_current_program_scene()
            return response.current_program_scene_name
        except Exception as e:
            logging.error(f"Error getting current scene: {e}")
            return None

    def set_media_source_file(self, source_name, file_path):
        """Updates a Media Source to play a specific video file."""
        if not self.req_client:
            logging.error("OBS not connected.")
            return False
        try:
            # OBS requires absolute paths
            abs_path = os.path.abspath(file_path)
            logging.info(f"Setting OBS Source '{source_name}' to file: {abs_path}")
            
            # Check if source exists (optional but good practice, skipping for speed)
            
            # 'local_file' is the standard setting key for VLC Source or Media Source
            self.req_client.set_input_settings(
                name=source_name,
                settings={"local_file": abs_path},
                overlay=True
            )
            return True
        except Exception as e:
            logging.error(f"Failed to set media file for source '{source_name}': {e}")
            return False