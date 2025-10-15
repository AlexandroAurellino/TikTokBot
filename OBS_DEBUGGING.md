# 🐛 Debugging Auto-Return to Main Scene

If the bot switches to product scenes but doesn't return to the main scene when videos end, follow these steps:

## ✅ Quick Checklist

### 1. **Verify OBS Media Source Settings**

Your media sources MUST be configured correctly:

1. Open OBS
2. Go to your product scene (e.g., `Product_Scene_1`)
3. Select your media source (video file)
4. Right-click → **Properties**
5. Check these settings:
   - ❌ **Uncheck "Loop"** - This is critical!
   - ✅ **Check "Restart playback when source becomes active"** (optional)
   - ✅ Make sure "Close file when inactive" is unchecked

**Why?** If "Loop" is enabled, the MediaInputPlaybackEnded event will NEVER fire!

### 2. **Test the Event System**

Run the OBS controller test:

```bash
cd backend
python obs_controller.py
```

This will:

- Connect to OBS
- Register event listener
- Wait for media events

Now manually:

1. Switch to a product scene in OBS
2. Let the video play until it ends
3. Watch the console - you should see: `TEST: Received event: MediaInputPlaybackEnded`

If you DON'T see this event:

- Your media source has "Loop" enabled
- Or your media source is not actually a media file (it's an image/browser source)

### 3. **Check Your Scene Configuration**

Verify your product scenes are in the video_scenes set:

```python
# In engine.py, add debug logging:
print(f"Main scene: {self.main_scene_name}")
print(f"Video scenes: {self.video_scenes}")
print(f"Product to scene map: {self.product_to_scene_map}")
```

The `video_scenes` should include all your product scenes EXCEPT the main scene.

### 4. **Enable Detailed Logging**

Add this at the top of `engine.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

This will show ALL events and debug information.

## 🔍 Common Issues & Solutions

### Issue 1: Event Never Fires

**Symptoms:**

- Scene switches correctly
- Video plays
- No event logged when video ends
- Stuck on product scene

**Causes:**

- Media source has "Loop" enabled
- Media source is not a video file
- Using Browser Source instead of Media Source

**Solution:**

```
1. In OBS, right-click your media source
2. Properties
3. UNCHECK "Loop"
4. Click OK
5. Test again
```

### Issue 2: Event Fires But Doesn't Switch Back

**Symptoms:**

- You see `[OBS EVENT] Media source 'X' finished playing.`
- But scene doesn't change

**Cause:** Scene name mismatch

**Debug:**
Check the log output - it should show:

```
[OBS EVENT] Current scene is: 'Product_Scene_1'
[ACTION] Product video ended in 'Product_Scene_1'. Returning to main scene 'Main_Camera'.
```

If you see:

```
[SKIPPED] Media ended but we're not in a product scene.
```

This means the current scene name doesn't match any scene in your `product_to_scene_map`.

**Solution:**

1. Check your config.json scene names EXACTLY match OBS
2. Scene names are case-sensitive: "Product_scene_1" ≠ "Product_Scene_1"
3. List your OBS scenes and copy names exactly

### Issue 3: Wrong Media Source

**Symptoms:**

- Event fires for wrong source
- Multiple media sources in scene

**Cause:** Multiple media sources with same name or event triggering for background music

**Solution:**
Make sure each product scene has only ONE media source, or filter by source name in the callback.

### Issue 4: Event Client Not Connected

**Symptoms:**

- No events logged at all
- Connection seems OK

**Cause:** Event client didn't initialize

**Debug:**
Check for this log line:

```
Event client created and callback registered for MediaInputPlaybackEnded
```

If missing, the event_callback wasn't passed correctly.

**Solution:**
Make sure in engine.py you're passing the callback:

```python
self.obs = OBSController(
    host=obs_host,
    port=obs_port,
    password=obs_password,
    event_callback=self.on_obs_event  # This line is critical!
)
```

## 🧪 Step-by-Step Testing

### Test 1: Manual Scene Test

```python
# Create test_obs_events.py
from obs_controller import OBSController
import time

def my_callback(event):
    print(f"✓ GOT EVENT: {event.event_type}")
    print(f"✓ DATA: {event.event_data}")

obs = OBSController(event_callback=my_callback)
if obs.connect():
    print("Connected! Now play a video in OBS...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
obs.disconnect()
```

Run this and play a video in OBS. You MUST see the event when video ends.

### Test 2: Check Media Source Type

In OBS, verify your source type:

- ✅ **Media Source** - Good! Events will fire
- ❌ **Browser Source** - Won't fire media events
- ❌ **Image** - Won't fire media events
- ❌ **VLC Video Source** - Different events

### Test 3: Verify Scene Names

```python
# Add to engine.py start() method:
print("\n" + "="*60)
print("CONFIGURATION DEBUG:")
print(f"Main Scene: '{self.main_scene_name}'")
print(f"Product Scenes: {list(self.video_scenes)}")
print(f"Scene Map: {self.product_to_scene_map}")
print("="*60 + "\n")
```

Make sure:

- Main scene is NOT in video_scenes
- All product scenes ARE in video_scenes
- Names match OBS exactly

## 💡 Alternative: Time-Based Return

If events still don't work, you can use a timer-based approach:

```python
# In engine.py, add this method:
def schedule_return_to_main(self, delay_seconds=30):
    """Schedule return to main scene after delay."""
    def delayed_return():
        time.sleep(delay_seconds)
        current = self.obs.get_current_scene()
        if current in self.video_scenes:
            logging.info(f"[TIMER] Returning to main scene after {delay_seconds}s")
            self.obs.switch_to_scene(self.main_scene_name)

    threading.Thread(target=delayed_return, daemon=True).start()

# Then in process_comment, after switching:
self.obs.switch_to_scene(target_scene)
self.schedule_return_to_main(delay_seconds=30)  # Return after 30 seconds
```

This is a backup solution if events don't work.

## 📋 Final Checklist

Before asking for help, verify:

- [ ] Media source "Loop" is UNCHECKED
- [ ] Media source is type "Media Source" (not Browser/VLC)
- [ ] Event callback is passed to OBSController
- [ ] Scene names in config.json match OBS exactly (case-sensitive)
- [ ] You see "Event client created" in logs
- [ ] Running `python obs_controller.py` shows events when video ends
- [ ] Main scene is NOT in the product_to_scene_map values
- [ ] OBS WebSocket version is compatible (v5.0+)

## 🔧 Advanced Debugging

### Enable OBS WebSocket Logging

1. In OBS: Tools → WebSocket Server Settings
2. Enable debug logging
3. Check OBS logs for event transmission

### Check OBS WebSocket Version

```python
# Add to obs_controller.py connect():
version = self.req_client.get_version()
print(f"OBS: {version.obs_version}")
print(f"WebSocket: {version.obs_web_socket_version}")
```

Make sure WebSocket version is 5.0.0 or higher.

### Monitor All Events

```python
# Temporarily add to _on_media_input_playback_ended:
def _on_media_input_playback_ended(self, event_data):
    print("="*60)
    print("RAW EVENT DATA:")
    print(event_data)
    print("="*60)
    # ... rest of method
```

This shows exactly what OBS is sending.

## ✅ Success Indicators

When working correctly, you should see:

```
[COMMENT] User123: 'show me the lamp'
[ACTION] Switching to scene 'Product_Scene_1' for 'Cosmic Glow Lamp'
✓ Successfully switched OBS scene to 'Product_Scene_1'.

... (video plays) ...

[OBS EVENT] Media source 'product_video.mp4' finished playing.
[OBS EVENT] Current scene is: 'Product_Scene_1'
[ACTION] Product video ended in 'Product_Scene_1'. Returning to main scene 'Main_Camera'.
✓ Successfully switched OBS scene to 'Main_Camera'.
```

If you see all of these messages, everything is working perfectly! 🎉
