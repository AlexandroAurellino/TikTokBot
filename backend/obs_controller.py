# backend/obs_controller.py

import obsws_python as obs
import logging

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
            logging.error(f"--> Check host={self.host}, port={self.port}")
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
            return
        
        try:
            scene_list_response = self.req_client.get_scene_list()
            if scene_list_response:
                available_scenes = [s['sceneName'] for s in scene_list_response.scenes]
                
                if scene_name in available_scenes:
                    self.req_client.set_current_program_scene(scene_name)
                    logging.info(f"✓ Successfully switched OBS scene to '{scene_name}'.")
                else:
                    logging.warning(f"✗ Scene '{scene_name}' not found in OBS.")
                    logging.warning(f"Available scenes: {available_scenes}")
            else:
                logging.error("Could not get a valid scene list from OBS.")
        except Exception as e:
            logging.error(f"An error occurred while switching scenes: {e}")
    
    def get_current_scene(self):
        """Gets the current active scene name."""
        if not self.req_client:
            logging.warning("Not connected to OBS. Cannot get current scene.")
            return None
        
        try:
            response = self.req_client.get_current_program_scene()
            return response.current_program_scene_name
        except Exception as e:
            logging.error(f"Error getting current scene: {e}")
            return None
    
    def get_media_input_status(self, source_name: str):
        """Gets the status of a media source."""
        if not self.req_client:
            return None
        
        try:
            response = self.req_client.get_media_input_status(source_name)
            return response
        except Exception as e:
            logging.error(f"Error getting media status for '{source_name}': {e}")
            return None


# Test block
if __name__ == '__main__':
    def test_callback(event):
        print(f"TEST: Received event: {event.event_type}")
        print(f"TEST: Event data: {event.event_data}")
    
    print("="*60)
    print("Testing OBS Controller with Event Handling")
    print("="*60)
    
    obs_ctrl = OBSController(event_callback=test_callback)
    
    if obs_ctrl.connect():
        print("\n✓ Connected to OBS successfully!")
        
        # Get current scene
        current = obs_ctrl.get_current_scene()
        print(f"✓ Current scene: {current}")
        
        print("\nNow play a media source in OBS and watch for the event...")
        print("Press Ctrl+C to stop testing")
        
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping test...")
    else:
        print("\n✗ Failed to connect to OBS")
    
    obs_ctrl.disconnect()
    print("Test completed.")