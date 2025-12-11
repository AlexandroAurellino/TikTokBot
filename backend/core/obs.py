import obsws_python as obs
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class OBSController:
    """A class to manage the connection and commands for OBS."""
    
    def __init__(self, host='localhost', port=4455, password='', event_callback=None):
        self.host = host
        self.port = port
        self.password = password
        self.event_callback = event_callback
        self.req_client = None
        self.event_client = None
    
    def connect(self):
        try:
            self.req_client = obs.ReqClient(host=self.host, port=self.port, password=self.password)
            
            if self.event_callback:
                self.event_client = obs.EventClient(host=self.host, port=self.port, password=self.password)
                self.event_client.callback.register(self._on_media_input_playback_ended)
            
            return True
        except Exception as e:
            logging.error(f"OBS Connect Failed: {e}")
            return False
    
    def _on_media_input_playback_ended(self, event_data):
        try:
            class SimpleEvent:
                def __init__(self, event_type, data):
                    self.event_type = event_type
                    self.event_data = data
            
            if self.event_callback:
                self.event_callback(SimpleEvent("MediaInputPlaybackEnded", event_data))
        except Exception as e:
            logging.error(f"Error in media callback: {e}")
    
    def disconnect(self):
        try:
            if self.event_client:
                self.event_client.disconnect()
                self.event_client = None
            if self.req_client:
                self.req_client.disconnect()
                self.req_client = None
        except Exception as e:
            logging.error(f"Disconnect error: {e}")
    
    def switch_to_scene(self, scene_name: str):
        if not self.req_client: return False
        try:
            self.req_client.set_current_program_scene(scene_name)
            return True
        except Exception as e:
            logging.error(f"Switch scene error: {e}")
            return False
    
    def get_current_scene(self):
        if not self.req_client: return None
        try:
            return self.req_client.get_current_program_scene().current_program_scene_name
        except: return None

    def set_media_source_file(self, source_name, file_path):
        if not self.req_client: return False
        try:
            abs_path = os.path.abspath(file_path)
            logging.info(f"Setting OBS Source '{source_name}' to: {abs_path}")
            self.req_client.set_input_settings(name=source_name, settings={"local_file": abs_path}, overlay=True)
            return True
        except Exception as e:
            logging.error(f"Set media file error: {e}")
            return False