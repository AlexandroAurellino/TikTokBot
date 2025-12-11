# 🎬 AI-Powered TikTok Live Shop Scene Changer

Automatically switch OBS scenes based on product requests in TikTok live stream comments using AI.

## ✨ Features

- **AI-Powered Detection**: Uses DeepSeek AI to understand product requests from comments
- **Fuzzy Matching**: Smart algorithm handles typos and variations in product names
- **Rate Limiting**: Prevents excessive scene switches (configurable)
- **Comment Caching**: Avoids re-processing similar comments
- **Auto-Return**: Automatically returns to main scene when product videos end
- **Web Dashboard**: Beautiful control panel for configuration and monitoring
- **Live Statistics**: Real-time stats on comments, switches, and performance
- **Robust Error Handling**: Comprehensive logging and graceful error recovery

## 📋 Requirements

- Python 3.10+
- OBS Studio with WebSocket plugin enabled
- TikTok account (must be live streaming)
- DeepSeek API key

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ai-scene-changer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**

```
flask
requests
python-dotenv
obsws-python
TikTokLive
```

### 3. Create Project Structure

```
ai-scene-changer/
├── backend/
│   ├── ai_processor.py
│   ├── engine.py
│   ├── main.py
│   ├── obs_controller.py
│   └── tiktok_listener.py
├── frontend/
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── script.js
├── config.json
└── README.md
```

### 4. Configure OBS

1. Open OBS Studio
2. Go to **Tools → WebSocket Server Settings**
3. Enable **Enable WebSocket server**
4. Note the port (default: 4455)
5. Set a password (optional but recommended)

### 5. Get DeepSeek API Key

1. Visit [deepseek.com](https://deepseek.com)
2. Sign up / Log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk-`)

### 6. Set Up Your Products and Scenes in OBS

For each product you want to showcase:

1. Create a new scene in OBS (e.g., `Product_Scene_1`)
2. Add your product video or image as a source
3. Make sure media sources are set to stop at end (not loop)
4. Note the exact scene names - you'll need these

## ⚙️ Configuration

### Option 1: Web Dashboard (Recommended)

1. Start the web server:

```bash
cd backend
python main.py
```

2. Open your browser to: `http://localhost:5000`

3. Fill in the configuration:

   - **TikTok Username**: Your TikTok handle (with @)
   - **DeepSeek API Key**: Your API key from deepseek.com
   - **OBS Settings**: Host, port, and password
   - **Main Scene Name**: The scene to return to after showing products
   - **Products**: List your products
   - **Scene Mapping**: Map each product to its OBS scene

4. Click **Save Settings**

### Option 2: Manual Configuration

Edit `config.json`:

```json
{
  "tiktok_username": "@yourusername",
  "deepseek_api_key": "sk-your-api-key-here",
  "obs_ws_host": "localhost",
  "obs_ws_port": 4455,
  "obs_ws_password": "your-password",
  "main_scene_name": "Main_Camera",
  "tiktok_reconnect_delay": 30,
  "comment_rate_limit": 2,
  "cache_duration_seconds": 300,
  "product_list": [
    "Cosmic Glow Lamp",
    "Stealth Gaming Mouse",
    "Ultra-Soft Hoodie"
  ],
  "product_to_scene_map": {
    "Cosmic Glow Lamp": "Product_Scene_1",
    "Stealth Gaming Mouse": "Product_Scene_2",
    "Ultra-Soft Hoodie": "Product_Scene_3"
  }
}
```

## 🎮 Usage

### Starting the Bot

**Via Web Dashboard:**

1. Open `http://localhost:5000`
2. Click **▶️ Start Bot**
3. Monitor live statistics

**Via Command Line:**

```bash
cd backend
python engine.py
```

### During Your Live Stream

1. Start your TikTok live stream
2. Start the bot (it will connect automatically)
3. When viewers comment requests like:
   - "show me the lamp"
   - "can I see the mouse?"
   - "hoodie please"
4. The bot will:
   - Detect the product request using AI
   - Switch to the corresponding scene
   - Return to main scene when video ends

### Stopping the Bot

**Via Web Dashboard:**

- Click **⏹️ Stop Bot**

**Via Command Line:**

- Press `Ctrl+C`

## 📊 Understanding the Statistics

The dashboard shows real-time stats:

- **Comments Processed**: Total comments analyzed
- **Scenes Switched**: Number of successful scene changes
- **Cache Hits**: Comments served from cache (faster)
- **Rate Limited**: Requests blocked to prevent spam
- **Errors**: Failed AI calls or connection issues

## 🔧 Advanced Configuration

### Rate Limiting

Prevents excessive scene switches:

```json
"comment_rate_limit": 2  // Max 2 switches per minute
```

### Comment Caching

Caches similar comments to reduce AI API calls:

```json
"cache_duration_seconds": 300  // Cache for 5 minutes
```

### Reconnection Delay

Time to wait before reconnecting to TikTok:

```json
"tiktok_reconnect_delay": 30  // 30 seconds
```

## 🐛 Troubleshooting

### Bot Won't Start

**Issue**: "Could not connect to OBS"

- **Solution**: Make sure OBS is running and WebSocket server is enabled
- Check that host/port/password match your OBS settings

**Issue**: "Failed to connect to TikTok"

- **Solution**: Make sure the username is correct and the user is currently live
- Try adding @ to the username

### Scenes Not Switching

**Issue**: Comments detected but no scene change

- **Solution**: Check that scene names in config exactly match OBS scene names (case-sensitive)
- Verify OBS connection in logs

**Issue**: AI not detecting products

- **Solution**:
  - Check DeepSeek API key is valid
  - Ensure product names in config are clear and descriptive
  - View logs to see AI responses

### Performance Issues

**Issue**: Slow response time

- **Solution**:
  - Increase cache duration to reduce AI calls
  - Ensure stable internet connection
  - Check DeepSeek API rate limits

## 📝 Best Practices

1. **Product Names**: Use clear, descriptive names

   - ✅ "Wireless Gaming Mouse"
   - ❌ "Product 1"

2. **Scene Organization**: Keep consistent naming

   - ✅ "Product_Mouse", "Product_Lamp"
   - ❌ Random names

3. **Video Sources**: Set media to stop at end, not loop

4. **Testing**: Test with the bot BEFORE going live

   - Use command line to test individual modules
   - Verify all scenes switch correctly

5. **Rate Limiting**: Start conservative (2/min) and adjust based on your stream

## 🔒 Security Notes

- Never commit `config.json` with your API keys
- Use strong passwords for OBS WebSocket
- Consider using HTTPS if exposing the dashboard to the internet
- The dashboard has no authentication - only run on trusted networks

## 🧪 Testing Individual Components

### Test TikTok Listener

```bash
cd backend
python tiktok_listener.py
```

Edit the file to set a username that's currently live.

### Test AI Processor

```bash
cd backend
python ai_processor.py
```

This will test the DeepSeek API with sample comments.

### Test OBS Controller

```bash
cd backend
python obs_controller.py
```

Make sure OBS is running first.

## 📖 How It Works

### Architecture Flow

```
TikTok Live Comment
    ↓
TikTok Listener (receives comment)
    ↓
AI Processor (analyzes intent)
    ↓
Fuzzy Matcher (finds product)
    ↓
Rate Limiter (checks if allowed)
    ↓
OBS Controller (switches scene)
    ↓
OBS Event (video ends)
    ↓
Auto-return to main scene
```

### AI Analysis

The system sends each comment to DeepSeek AI with:

- List of available products
- Instructions to detect product requests
- Request for structured JSON response

Example:

```
Comment: "can I see the lamp?"
AI Response: {
  "intent": "product_request",
  "product_name": "Cosmic Glow Lamp"
}
```

### Fuzzy Matching

The fuzzy matcher handles variations:

- "lamp" → "Cosmic Glow Lamp"
- "gaming mouse" → "Stealth Gaming Mouse"
- "hoodie soft" → "Ultra-Soft Hoodie"

Uses three methods:

1. **Substring matching**: Exact partial matches
2. **Word overlap**: Common words between phrases
3. **String similarity**: Handles typos with SequenceMatcher

## 🎯 Example Use Cases

### Fashion Store

```json
"product_list": [
  "Black Leather Jacket",
  "Denim Jeans",
  "White Sneakers"
]
```

Viewers say:

- "Show me the jacket" → Switches to jacket scene
- "Can I see those jeans?" → Switches to jeans scene

### Tech Store

```json
"product_list": [
  "Wireless Earbuds",
  "Portable Charger",
  "Phone Case"
]
```

Viewers say:

- "earbuds" → Switches to earbuds scene
- "show the charger" → Switches to charger scene

### Beauty Products

```json
"product_list": [
  "Matte Lipstick",
  "Face Serum",
  "Eye Shadow Palette"
]
```

Viewers say:

- "lipstick please" → Switches to lipstick scene
- "can you show the serum" → Switches to serum scene

## 🔄 Updating the System

### Adding New Products

1. Add product to OBS:

   - Create new scene with product media
   - Note the exact scene name

2. Update configuration:

   - Add product name to `product_list`
   - Add mapping to `product_to_scene_map`

3. Restart the bot for changes to take effect

### Changing Settings

Changes to `config.json` require a bot restart:

1. Stop the bot
2. Modify settings
3. Start the bot again

## 💡 Tips for Better Results

### Optimizing AI Detection

1. **Use specific product names**: "RGB Gaming Keyboard" vs "Keyboard"
2. **Avoid similar names**: Don't have both "Blue Shirt" and "Blue Jacket"
3. **Keep names under 5 words**: Shorter names = better matching

### Optimizing Performance

1. **Increase cache duration** for repetitive comments
2. **Adjust rate limit** based on comment volume
3. **Use shorter video clips** for faster cycles

### Enhancing Viewer Experience

1. **Announce products clearly**: Tell viewers what to ask for
2. **Use consistent naming**: Say the exact product names on stream
3. **Respond quickly**: Lower rate limits for more responsive switching

## 🆘 Common Error Messages

### "deepseek_api_key not found in config.json"

- Your config.json is missing the API key field
- Add: `"deepseek_api_key": "sk-your-key"`

### "Scene 'Product_Scene_1' not found in OBS"

- The scene name in your config doesn't match OBS
- Check for typos and case sensitivity
- List available scenes in OBS to verify names

### "Product list and scene map don't match"

- Every product in `product_list` must have a scene in `product_to_scene_map`
- Check for missing or extra entries

### "Could not find a confident fuzzy match"

- AI detected a product but couldn't match it to your list
- Check logs to see what the AI returned
- Consider adding alternative names or adjusting your product list

## 📈 Performance Optimization

### For High-Traffic Streams

1. **Increase cache duration**:

```json
"cache_duration_seconds": 600  // 10 minutes
```

2. **Raise rate limit gradually**:

```json
"comment_rate_limit": 5  // Start at 2, increase if needed
```

3. **Monitor statistics**: Watch cache hit rate and adjust accordingly

### For Better AI Accuracy

1. **Use descriptive product names**: Include key attributes
2. **Test with real comments**: Run test streams before going live
3. **Check logs regularly**: See what AI is detecting

## 🔌 API Endpoints Reference

The web dashboard uses these REST API endpoints:

### GET `/api/settings`

Returns current configuration

### POST `/api/settings`

Saves new configuration

- Validates all fields
- Returns errors if invalid

### POST `/api/start`

Starts the bot

- Returns error if already running
- Creates new thread for TikTok listener

### POST `/api/stop`

Stops the bot

- Returns error if not running
- Waits for graceful shutdown

### GET `/api/status`

Returns bot status and statistics

```json
{
  "running": true,
  "stats": {
    "comments_processed": 45,
    "scenes_switched": 12,
    "cache_hits": 8,
    "rate_limited": 2,
    "errors": 0
  }
}
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Additional AI providers (OpenAI, Anthropic)
- Scene transition effects
- Multi-language support
- Analytics dashboard
- Mobile app

## 📄 License

MIT License - Feel free to use and modify for your needs.

## 🙏 Acknowledgments

- **DeepSeek** for the AI API
- **OBS Studio** for streaming software
- **TikTokLive** Python library for TikTok integration

## 📞 Support

For issues and questions:

1. Check this README thoroughly
2. Review logs in the console
3. Test individual components
4. Open an issue on GitHub

---

**Happy Streaming! 🎥✨**
