# Columbia Insurance Automation Bot

Automation bot for Columbia Insurance portal - handles login and quote form filling.

## Structure

- `columbia_automation.py` - **Single file** containing login and quote automation (simpler than Guard/Encova)
- `config.py` - Configuration and environment variables
- `webhook_server.py` - Flask webhook server for receiving requests
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration for Railway deployment
- `railway.json` - Railway deployment configuration

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Set environment variables (create `.env` file):
```
COLUMBIA_USERNAME=agt41297
COLUMBIA_PASSWORD=Columbia41297
WEBHOOK_PORT=5001
BROWSER_HEADLESS=true
```

3. Run webhook server:
```bash
python webhook_server.py
```

4. Test locally:
```bash
python test_local.py
```

## API Endpoints

- `POST /webhook` - Start automation task
- `GET /task/<task_id>/status` - Get task status
- `GET /tasks` - List all tasks
- `GET /health` - Health check
- `GET /traces` - List trace files
- `GET /trace/<task_id>` - Download trace file

## Webhook Payload

```json
{
  "action": "start_automation",
  "task_id": "optional_unique_id",
  "quote_data": {
    // Quote form fields (to be defined based on form structure)
  }
}
```

## Deployment

### Railway Deployment

1. **Create a new Railway project:**
   - Go to [Railway.app](https://railway.app)
   - Create a new project
   - Connect your GitHub repository (or deploy from local)

2. **Configure Environment Variables in Railway:**
   - Go to your Railway project → Variables
   - Add the following environment variables:
     ```
     COLUMBIA_USERNAME=agt41297
     COLUMBIA_PASSWORD=Columbia41297
     BROWSER_HEADLESS=true
     MAX_WORKERS=3
     ```
   - **Note:** Railway automatically provides `PORT` env var, don't set it manually

3. **Deploy:**
   - Railway will automatically detect the `Dockerfile` and `railway.json`
   - The app will build and deploy automatically
   - Railway will assign a public URL (e.g., `https://your-app.up.railway.app`)

4. **Test Railway Deployment:**
   ```bash
   # Update SERVER_URL in test_railway.py with your Railway URL
   python test_railway.py
   ```

### Railway Configuration

- **Dockerfile:** Automatically builds the app with all dependencies
- **railway.json:** Configures Railway deployment settings
- **PORT:** Railway automatically provides `PORT` env var (config.py handles it)
- **Headless Mode:** Automatically enabled on Railway (Linux environment)
- **Health Check:** `/health` endpoint for Railway health checks

### Environment Variables

Required for Railway:
- `COLUMBIA_USERNAME` - Columbia portal username
- `COLUMBIA_PASSWORD` - Columbia portal password
- `BROWSER_HEADLESS=true` - Set to true for Railway (auto-detected on Linux)

Optional:
- `MAX_WORKERS=3` - Number of concurrent tasks (default: 3)
- `ENABLE_TRACING=true` - Enable Playwright tracing (default: true)
- `CLEANUP_LOGS_DAYS=7` - Log retention days (default: 7)

## Notes

- **Single file** - Everything in `columbia_automation.py` (simpler than Guard/Encova)
- No Gmail IMAP integration needed (no 2FA)
- Simpler than Guard/Encova automation
- Form structure needs to be inspected and implemented in `fill_quote_details()` method

