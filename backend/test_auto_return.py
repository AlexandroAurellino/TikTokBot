# backend/test_auto_return.py

"""
Simple interactive test for the auto-return feature.
This will switch to a product scene and wait for the video to end.
"""

import json
import time
import sys
from pathlib import Path
from obs_controller import OBSController

def main():
    print("\n" + "="*70)
    print("🎬 Auto-Return Feature Test")
    print("="*70)
    print()
    
    # Load config
    config_path = Path(__file__).parent.parent / 'config.json'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error loading config.json: {e}")
        return
    
    main_scene = config.get('main_scene_name', 'Scene_A')
    product_to_scene = config.get('product_to_scene_map', {})
    
    if not product_to_scene:
        print("❌ No product scenes configured in config.json")
        return
    
    product_scenes = list(product_to_scene.values())
    video_scenes = set(s for s in product_scenes if s != main_scene)
    
    print(f"📋 Configuration:")
    print(f"   Main Scene: {main_scene}")
    print(f"   Product Scenes: {list(video_scenes)}")
    print()
    
    # Track returns
    returned_to_main = False
    current_test_scene = None
    
    def event_handler(event):
        nonlocal returned_to_main, current_test_scene
        
        if event.event_type == "MediaInputPlaybackEnded":
            source_name = event.event_data.get("inputName", "Unknown")
            print(f"\n🎬 EVENT: Media '{source_name}' finished playing!")
            
            # Get current scene
            current_scene = obs.get_current_scene()
            print(f"   Current scene: {current_scene}")
            
            # Check if we're in a product scene
            if current_scene in video_scenes:
                print(f"   ✓ In product scene, switching to main scene...")
                obs.switch_to_scene(main_scene)
                time.sleep(1)
                
                # Verify we switched
                new_scene = obs.get_current_scene()
                if new_scene == main_scene:
                    print(f"   ✅ SUCCESS! Returned to main scene '{main_scene}'")
                    returned_to_main = True
                else:
                    print(f"   ❌ FAILED! Still on '{new_scene}'")
            else:
                print(f"   ℹ️  Not in a product scene, no action needed")
    
    # Create OBS controller with event callback
    obs = OBSController(
        host=config.get('obs_ws_host', 'localhost'),
        port=config.get('obs_ws_port', 4455),
        password=config.get('obs_ws_password', ''),
        event_callback=event_handler
    )
    
    # Connect
    print("🔌 Connecting to OBS...")
    if not obs.connect():
        print("❌ Failed to connect to OBS")
        print("   Make sure OBS is running and WebSocket is enabled")
        return
    
    print("✅ Connected to OBS!")
    print()
    
    # Get current scene
    current = obs.get_current_scene()
    print(f"📍 Current OBS scene: {current}")
    print()
    
    # Choose a product scene to test
    print("Available product scenes:")
    for i, scene in enumerate(video_scenes, 1):
        print(f"   {i}. {scene}")
    print()
    
    try:
        choice = input(f"Enter number (1-{len(video_scenes)}) or press Enter for first scene: ").strip()
        if choice:
            scene_index = int(choice) - 1
            if 0 <= scene_index < len(video_scenes):
                test_scene = list(video_scenes)[scene_index]
            else:
                test_scene = list(video_scenes)[0]
        else:
            test_scene = list(video_scenes)[0]
    except:
        test_scene = list(video_scenes)[0]
    
    current_test_scene = test_scene
    
    print()
    print("="*70)
    print("🎯 TEST PROCEDURE:")
    print("="*70)
    print(f"1. I will switch OBS to: '{test_scene}'")
    print(f"2. The video in that scene should play")
    print(f"3. When the video ends, it should auto-return to: '{main_scene}'")
    print()
    print("⚠️  IMPORTANT: Make sure the media source does NOT have 'Loop' checked!")
    print()
    input("Press Enter when ready to start the test...")
    
    # Switch to the product scene
    print()
    print(f"🎬 Switching to '{test_scene}'...")
    obs.switch_to_scene(test_scene)
    time.sleep(1)
    
    # Verify switch
    new_scene = obs.get_current_scene()
    if new_scene == test_scene:
        print(f"✅ Successfully switched to '{test_scene}'")
    else:
        print(f"❌ Switch failed. Current scene: '{new_scene}'")
        obs.disconnect()
        return
    
    print()
    print("="*70)
    print("⏳ WAITING FOR VIDEO TO END...")
    print("="*70)
    print("The video should now be playing in OBS.")
    print("This script is listening for the MediaInputPlaybackEnded event.")
    print()
    print("If the video doesn't end or loops, press Ctrl+C to stop.")
    print("-"*70)
    
    # Wait for the event (max 5 minutes)
    timeout = 300
    start_time = time.time()
    
    try:
        while time.time() - start_time < timeout:
            time.sleep(1)
            
            if returned_to_main:
                break
            
            # Show progress every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"   Still waiting... ({elapsed}s elapsed)")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    
    print()
    print("="*70)
    print("TEST RESULTS")
    print("="*70)
    
    if returned_to_main:
        print("✅ SUCCESS! The auto-return feature is WORKING!")
        print()
        print("What happened:")
        print(f"   1. ✓ Switched to '{test_scene}'")
        print(f"   2. ✓ Video played until the end")
        print(f"   3. ✓ Received MediaInputPlaybackEnded event")
        print(f"   4. ✓ Automatically returned to '{main_scene}'")
        print()
        print("Your setup is configured correctly! 🎉")
    else:
        print("❌ FAILED - Auto-return did NOT work")
        print()
        print("Possible reasons:")
        print("   1. Media source has 'Loop' enabled (MOST COMMON)")
        print("      → Right-click media source → Properties → Uncheck 'Loop'")
        print()
        print("   2. Video is still playing (not finished yet)")
        print("      → Wait longer or use a shorter test video")
        print()
        print("   3. Media source is not a video file")
        print("      → Check that you're using 'Media Source' not 'Browser Source'")
        print()
        print("   4. No media source in the scene")
        print(f"      → Add a video to '{test_scene}'")
        print()
        print("To diagnose further, run:")
        print("   python diagnose.py")
    
    print("="*70)
    
    # Cleanup
    obs.disconnect()
    print("\n✓ Disconnected from OBS")

if __name__ == '__main__':
    main()