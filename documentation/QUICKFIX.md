# ⚡ Quick Fix: Auto-Return Not Working

## 🎯 The #1 Solution (Works 90% of the time)

Your media sources in OBS have **"Loop" enabled**. This prevents the end-of-video event from firing.

### Fix It in 30 Seconds:

1. **Open OBS**
2. **Go to your product scene** (e.g., Product_Scene_1)
3. **Right-click your video/media source**
4. **Click "Properties"**
5. **UNCHECK the box that says "Loop"** ✅
6. **Click "OK"**
7. **Repeat for ALL product scenes**

That's it! Test again - it should work now.

---

## 🧪 Test If It's Fixed

### Quick Test (30 seconds):

```bash
cd backend
python test_auto_return.py
```

This will:

- Switch to a product scene
- Wait for the video to end
- Confirm if it returns to main scene

### What You Should See:

```
✅ SUCCESS! The auto-return feature is WORKING!

What happened:
   1. ✓ Switched to 'Product_Scene_1'
   2. ✓ Video played until the end
   3. ✓ Received MediaInputPlaybackEnded event
   4. ✓ Automatically returned to 'Main_Camera'
```

---

## 🔍 Still Not Working?

### Run Full Diagnostic:

```bash
cd backend
python diagnose.py
```

This checks:

- OBS connection
- Scene configuration
- Media sources
- Event system

### Common Issues Beyond Loop:

| Issue               | Solution                                                         |
| ------------------- | ---------------------------------------------------------------- |
| Wrong source type   | Use "Media Source" not "Browser Source" or "Image"               |
| Scene name mismatch | Check config.json scene names match OBS exactly (case-sensitive) |
| No media in scene   | Add a video file to your product scenes                          |
| OBS version too old | Update OBS to latest version (WebSocket 5.0+)                    |

---

## ✅ Verification Checklist

Before running your bot:

- [ ] Loop is UNCHECKED on all media sources
- [ ] Media sources are type "Media Source" (not Browser/VLC/Image)
- [ ] Scene names in config.json match OBS exactly
- [ ] Main scene is NOT in product_to_scene_map
- [ ] `python test_auto_return.py` shows SUCCESS

---

## 📱 Quick Reference

### Where is Loop Setting?

```
OBS → Sources Panel → Right-click media source → Properties → Loop checkbox
```

### How to Check Source Type?

```
OBS → Sources Panel → Look at the icon next to the source name
🎬 = Media Source (correct)
🌐 = Browser Source (wrong - won't fire events)
🖼️ = Image (wrong - won't fire events)
```

### Where is WebSocket?

```
OBS → Tools → WebSocket Server Settings → Enable checkbox
```

---

## 🎓 Understanding the Flow

```
Comment received
    ↓
AI detects product
    ↓
Switch to Product Scene ✅ (Working)
    ↓
Video plays
    ↓
Video ends → EVENT SHOULD FIRE HERE ← This is the problem
    ↓
Return to Main Scene ❌ (Not working)
```

**The Loop checkbox prevents the event from firing.**

When Loop is ON:

- Video plays
- Video ends
- Video immediately restarts
- No "ended" event ever fires
- Never returns to main scene

When Loop is OFF:

- Video plays
- Video ends
- "MediaInputPlaybackEnded" event fires ✅
- Bot catches event
- Switches back to main scene ✅

---

## 🚀 After Fixing

Once fixed, your workflow will be:

1. Viewer comments: "show me the lamp"
2. Bot switches to Product_Scene_1 (with lamp video)
3. Video plays automatically
4. Video ends
5. **Automatically returns to main scene** ← Now working!
6. Ready for next request

Perfect hands-free operation! 🎉

---

## 📞 Need More Help?

1. **Run diagnostics**: `python diagnose.py`
2. **Check detailed guide**: See `DEBUGGING_MEDIA_EVENTS.md`
3. **Test individual components**: `python obs_controller.py`
4. **Enable debug logging**: Change `logging.INFO` to `logging.DEBUG` in engine.py

---

**TL;DR: Uncheck Loop on your media sources in OBS. That's 90% of cases. Done!** ✅
