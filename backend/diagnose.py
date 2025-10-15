# backend/diagnose.py

"""
Diagnostic script to identify why auto-return isn't working.
Run this to check your OBS setup and configuration.
"""

import json
import sys
from pathlib import Path
import obsws_python as obs
import time

print("="*70)
print("🔍 AI Scene Changer - Auto-Return Diagnostic Tool")
print("="*70)
print()

# Load configuration
config_path = Path(__file__).parent.parent / 'config.json'
try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    print("✓ Configuration loaded successfully")
except Exception as e:
    print(f"✗ ERROR: Could not load config.json: {e}")
    sys.exit(1)

# Extract settings
obs_host = config.get('obs_ws_host', 'localhost')
obs_port = config.get('obs_ws_port', 4455)
obs_password = config.get('obs_ws_password', '')
main_scene = config.get('main_scene_name', 'Scene_A')
product_scenes = list(config.get('product_to_scene_map', {}).values())

print(f"  Host: {obs_host}")
print(f"  Port: {obs_port}")
print(f"  Main Scene: {main_scene}")
print(f"  Product Scenes: {product_scenes}")
print()

# Test 1: Connection
print("-" * 70)
print("TEST 1: OBS Connection")
print("-" * 70)

try:
    req_client = obs.ReqClient(host=obs_host, port=obs_port, password=obs_password)
    version = req_client.get_version()
    print(f"✓ Connected to OBS successfully!")
    print(f"  OBS Version: {version.obs_version}")
    print(f"  WebSocket Version: {version.obs_web_socket_version}")
    
    # Check WebSocket version
    ws_version = version.obs_web_socket_version
    if ws_version.startswith('5.'):
        print(f"✓ WebSocket version {ws_version} is compatible")
    else:
        print(f"⚠ WebSocket version {ws_version} - events may not work correctly")
        print("  Consider updating OBS to the latest version")
except Exception as e:
    print(f"✗ FAILED to connect to OBS: {e}")
    print("\nTroubleshooting:")
    print("  1. Is OBS running?")
    print("  2. Is WebSocket Server enabled? (Tools → WebSocket Server Settings)")
    print(f"  3. Is the port correct? ({obs_port})")
    print("  4. Is the password correct?")
    sys.exit(1)

print()

# Test 2: Scene Configuration
print("-" * 70)
print("TEST 2: Scene Configuration")
print("-" * 70)

try:
    scene_list = req_client.get_scene_list()
    available_scenes = [s['sceneName'] for s in scene_list.scenes]
    
    print(f"Found {len(available_scenes)} scenes in OBS:")
    for scene in available_scenes:
        is_main = "← MAIN SCENE" if scene == main_scene else ""
        is_product = "← PRODUCT SCENE" if scene in product_scenes else ""
        marker = is_main or is_product
        print(f"  • {scene} {marker}")
    
    print()
    
    # Check main scene exists
    if main_scene in available_scenes:
        print(f"✓ Main scene '{main_scene}' found in OBS")
    else:
        print(f"✗ ERROR: Main scene '{main_scene}' NOT found in OBS!")
        print(f"  Available scenes: {available_scenes}")
        print(f"  Update your config.json with the correct main scene name")
    
    # Check product scenes exist
    missing_scenes = [s for s in product_scenes if s not in available_scenes]
    if not missing_scenes:
        print(f"✓ All {len(product_scenes)} product scenes found in OBS")
    else:
        print(f"✗ ERROR: Some product scenes NOT found in OBS:")
        for scene in missing_scenes:
            print(f"  • {scene}")
        print(f"  Update your config.json or create these scenes in OBS")
    
    # Check for duplicates
    if main_scene in product_scenes:
        print(f"⚠ WARNING: Main scene is also listed as a product scene!")
        print(f"  This will prevent auto-return from working")
        print(f"  The main scene should NOT be in product_to_scene_map values")
    
except Exception as e:
    print(f"✗ ERROR getting scene list: {e}")

print()

# Test 3: Media Sources Check
print("-" * 70)
print("TEST 3: Media Sources in Product Scenes")
print("-" * 70)

for scene_name in product_scenes:
    if scene_name not in available_scenes:
        continue
    
    try:
        scene_items = req_client.get_scene_item_list(scene_name)
        media_sources = [
            item for item in scene_items.scene_items 
            if item.get('inputKind') == 'ffmpeg_source'  # Media Source type
        ]
        
        if media_sources:
            print(f"✓ Scene '{scene_name}':")
            for source in media_sources:
                source_name = source.get('sourceName', 'Unknown')
                print(f"  • Media Source: {source_name}")
                
                # Try to get media properties
                try:
                    status = req_client.get_media_input_status(source_name)
                    print(f"    Duration: {status.media_duration}ms")
                    print(f"    Loop: {getattr(status, 'media_loop', 'Unknown')}")
                except:
                    pass
        else:
            print(f"⚠ Scene '{scene_name}': No media sources found")
            print(f"  This scene may not trigger playback events")
            
    except Exception as e:
        print(f"  Could not inspect scene: {e}")

print()

# Test 4: Event System
print("-" * 70)
print("TEST 4: Event System Test")
print("-" * 70)
print("Testing if OBS sends media playback events...")
print()

event_received = False

def event_callback(event_data):
    global event_received
    event_received = True
    print(f"✓ SUCCESS! Received MediaInputPlaybackEnded event!")
    print(f"  Source: {event_data.get('inputName', 'Unknown')}")
    print()

try:
    event_client = obs.EventClient(host=obs_host, port=obs_port, password=obs_password)
    event_client.callback.register(event_callback)
    print("✓ Event listener registered")
    print()
    print("=" * 70)
    print("MANUAL TEST REQUIRED:")
    print("=" * 70)
    print("1. Switch to one of your product scenes in OBS")
    print("2. Make sure the media source does NOT have 'Loop' checked")
    print("3. Let the video play until it ends")
    print("4. Watch this window for the event notification")
    print()
    print("Waiting for media playback to end... (Press Ctrl+C to skip)")
    print("-" * 70)
    
    timeout = 60  # Wait up to 60 seconds
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            time.sleep(1)
            if event_received:
                break
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    
    event_client.disconnect()
    
    if event_received:
        print("=" * 70)
        print("✓ EVENT SYSTEM IS WORKING!")
        print("=" * 70)
        print("The auto-return feature should work correctly.")
        print()
    else:
        print("=" * 70)
        print("✗ NO EVENT RECEIVED")
        print("=" * 70)
        print("Possible causes:")
        print("  1. Media source has 'Loop' enabled (most common)")
        print("  2. Video hasn't finished playing yet")
        print("  3. Media source is not a proper media file")
        print("  4. Using VLC Video Source instead of Media Source")
        print()
        print("SOLUTION:")
        print("  1. In OBS, right-click your media source → Properties")
        print("  2. UNCHECK the 'Loop' checkbox")
        print("  3. Click OK")
        print("  4. Run this diagnostic again")
        print()
    
except Exception as e:
    print(f"✗ ERROR setting up event listener: {e}")

# Cleanup
req_client.disconnect()

print()
print("=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print()
print("Summary:")
print("  If all tests passed and you received the event,")
print("  the auto-return feature should work correctly.")
print()
print("  If you did NOT receive the event:")
print("  → Check that 'Loop' is UNCHECKED on your media sources")
print("  → This is the #1 reason auto-return doesn't work")
print()
print("Need more help? Check DEBUGGING_MEDIA_EVENTS.md")
print("=" * 70)