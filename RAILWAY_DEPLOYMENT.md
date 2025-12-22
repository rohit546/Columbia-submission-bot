# Columbia Automation - Railway Deployment Guide

Complete guide for deploying Columbia Insurance Automation to Railway.

## Prerequisites

- Railway account ([railway.app](https://railway.app))
- GitHub repository (optional, can deploy from local)
- Columbia Insurance portal credentials

## Step 1: Create Railway Project

1. Go to [Railway.app](https://railway.app) and sign in
2. Click "New Project"
3. Choose one of:
   - **Deploy from GitHub repo** (recommended)
   - **Deploy from local directory** (using Railway CLI)

## Step 2: Configure Environment Variables

In your Railway project dashboard:

1. Go to **Variables** tab
2. Add the following environment variables:

### Required Variables:
```
COLUMBIA_USERNAME=agt41297
COLUMBIA_PASSWORD=Columbia41297
BROWSER_HEADLESS=true
```

### Optional Variables (with defaults):
```
MAX_WORKERS=3
ENABLE_TRACING=true
CLEANUP_LOGS_DAYS=7
CLEANUP_TRACES_DAYS=30
CLEANUP_SESSIONS_DAYS=7
```

**Important Notes:**
- Railway automatically provides `PORT` environment variable - **DO NOT** set it manually
- `BROWSER_HEADLESS=true` is required for Railway (Linux environment)
- All other variables have sensible defaults

## Step 3: Deploy

Railway will automatically:
1. Detect the `Dockerfile` in your project
2. Build the Docker image with all dependencies
3. Install Playwright and Chromium
4. Start the webhook server on the port Railway provides

### Build Process:
- Installs system dependencies for Chromium
- Installs Python dependencies from `requirements.txt`
- Installs Playwright browsers (`playwright install chromium`)
- Sets up directories (logs, sessions, traces, debug)

### Deployment Settings:
- **Start Command:** `python webhook_server.py` (from `railway.json`)
- **Restart Policy:** ON_FAILURE (max 10 retries)
- **Health Check:** `/health` endpoint (checks every 30s)

## Step 4: Get Your Railway URL

1. After deployment, Railway will assign a public URL
2. Go to **Settings** → **Networking**
3. Generate a public domain (e.g., `https://columbia-bot-production.up.railway.app`)
4. Copy this URL for your Next.js app/webhook calls

## Step 5: Test Deployment

### Update Test File:
1. Open `test_railway.py`
2. Update `RAILWAY_URL` with your Railway URL:
   ```python
   RAILWAY_URL = "https://your-app.up.railway.app"
   ```

### Run Tests:
```bash
python test_railway.py
```

This will test:
- Server health check
- Full automation (tenant)
- Full automation (owner)
- Minimal data (required fields only)

## Step 6: Monitor Deployment

### Railway Dashboard:
- **Deployments:** View build logs and deployment status
- **Metrics:** CPU, Memory, Network usage
- **Logs:** Real-time application logs
- **Variables:** Manage environment variables

### Application Logs:
Check logs in Railway dashboard or via Railway CLI:
```bash
railway logs
```

### Health Check:
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "columbia-automation",
  "timestamp": "2025-01-XX...",
  "active_workers": 0,
  "max_workers": 3,
  "queue_size": 0
}
```

## Troubleshooting

### Build Fails:
- Check Railway build logs
- Ensure `Dockerfile` is in root directory
- Verify all dependencies in `requirements.txt`

### App Crashes:
- Check application logs in Railway dashboard
- Verify environment variables are set correctly
- Check if `BROWSER_HEADLESS=true` is set

### Health Check Fails:
- Ensure app is listening on `0.0.0.0` (not `localhost`)
- Check if `PORT` env var is being used correctly
- Verify `/health` endpoint is accessible

### Browser Issues:
- Ensure `BROWSER_HEADLESS=true` is set
- Check if all system dependencies are installed (in Dockerfile)
- Verify Playwright browsers are installed (`playwright install chromium`)

### Timeout Issues:
- Increase `BROWSER_TIMEOUT` if needed
- Check Railway resource limits (CPU/Memory)
- Consider increasing `MAX_WORKERS` if tasks are queuing

## API Endpoints

Once deployed, your Railway URL provides:

- `POST /webhook` - Start automation task
- `GET /task/<task_id>/status` - Get task status
- `GET /tasks` - List all tasks
- `GET /health` - Health check
- `GET /traces` - List trace files
- `GET /trace/<task_id>` - Download trace file

## Example Webhook Request

```bash
curl -X POST https://your-app.up.railway.app/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "start_automation",
    "task_id": "test_001",
    "quote_data": {
      "person_entering_risk": "John Doe",
      "person_entering_risk_email": "john.doe@example.com",
      "company_name": "Test Company LLC",
      "mailing_address": "280 Griffin Street, McDonough, GA 30253"
    }
  }'
```

## Next Steps

1. **Integrate with Next.js App:**
   - Update your Next.js app to use the Railway URL
   - Send webhook requests to `https://your-app.up.railway.app/webhook`

2. **Set Up Monitoring:**
   - Configure Railway alerts for deployment failures
   - Monitor application logs for errors
   - Set up external monitoring (optional)

3. **Scale (if needed):**
   - Railway automatically scales based on traffic
   - Adjust `MAX_WORKERS` based on your needs
   - Monitor resource usage in Railway dashboard

## Support

For issues:
1. Check Railway build/deployment logs
2. Check application logs
3. Verify environment variables
4. Test locally first with `test_local.py`
5. Test Railway deployment with `test_railway.py`

