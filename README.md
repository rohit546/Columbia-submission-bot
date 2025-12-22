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

Deploy to Railway using the Dockerfile. Railway will automatically:
- Set `PORT` environment variable
- Run in headless mode
- Handle health checks

## Notes

- **Single file** - Everything in `columbia_automation.py` (simpler than Guard/Encova)
- No Gmail IMAP integration needed (no 2FA)
- Simpler than Guard/Encova automation
- Form structure needs to be inspected and implemented in `fill_quote_details()` method

