# Railway Troubleshooting Guide

## Issue: "Failed to resolve" or DNS Error

### Problem
When testing the Railway deployment, you get:
```
Failed to resolve 'your-app.up.railway.app'
NameResolutionError
```

### Solution

**The Railway service is not publicly accessible yet!**

1. **Go to Railway Dashboard:**
   - Open your Railway project
   - Click on your service (the one running the webhook server)

2. **Enable Public Domain:**
   - Go to **Settings** tab
   - Scroll to **Networking** section
   - Click **Generate Domain** or **Settings** next to Networking
   - Railway will generate a public URL like: `https://your-service-production.up.railway.app`

3. **Copy the Exact URL:**
   - Copy the URL Railway provides
   - **IMPORTANT:** Remove any trailing slash
   - Update `RAILWAY_URL` in `test_railway.py`:
     ```python
     RAILWAY_URL = "https://your-service-production.up.railway.app"  # NO trailing slash!
     ```

4. **Verify Service is Running:**
   - Check Railway deployment logs
   - Look for: `Running on http://0.0.0.0:8080` or similar
   - Should see: `Columbia Automation Webhook Server starting`

## Issue: Server Running But Not Accessible

### Check These:

1. **Port Configuration:**
   - Railway automatically sets `PORT` environment variable
   - Your app should use this: `WEBHOOK_PORT = int(os.getenv('PORT', 5001))`
   - ✅ Your config.py already handles this correctly

2. **Host Configuration:**
   - Server must listen on `0.0.0.0` (not `localhost` or `127.0.0.1`)
   - ✅ Your webhook_server.py uses `WEBHOOK_HOST = '0.0.0.0'` which is correct

3. **Health Check Endpoint:**
   - Test: `https://your-app.up.railway.app/health`
   - Should return JSON with `"status": "healthy"`

## Issue: 404 Not Found

### Check URL Format:

✅ **Correct:**
```
https://your-app.up.railway.app/health
https://your-app.up.railway.app/webhook
```

❌ **Wrong (trailing slash):**
```
https://your-app.up.railway.app/health/
https://your-app.up.railway.app/webhook/
```

## Issue: Connection Timeout

1. **Check Railway Deployment Status:**
   - Go to Railway dashboard
   - Check if deployment succeeded
   - Look for errors in build logs

2. **Check Environment Variables:**
   - Verify all required variables are set:
     - `COLUMBIA_USERNAME`
     - `COLUMBIA_PASSWORD`
     - `BROWSER_HEADLESS=true`

3. **Check Application Logs:**
   - Railway dashboard → Your service → Logs
   - Look for startup errors
   - Check if server started successfully

## Issue: 500 Internal Server Error

1. **Check Application Logs:**
   - Railway dashboard → Logs tab
   - Look for Python errors or tracebacks

2. **Check Environment Variables:**
   - Make sure all required variables are set correctly
   - Check for typos in variable names

3. **Test Health Endpoint:**
   ```bash
   curl https://your-app.up.railway.app/health
   ```

## Quick Verification Steps

1. **Verify Deployment:**
   ```
   Railway Dashboard → Your Service → Deployments
   Status should be: ✅ Active
   ```

2. **Check Logs:**
   ```
   Railway Dashboard → Your Service → Logs
   Should see: "Columbia Automation Webhook Server starting on 0.0.0.0:8080"
   ```

3. **Test Health Endpoint:**
   ```bash
   curl https://your-app.up.railway.app/health
   ```
   Should return:
   ```json
   {
     "status": "healthy",
     "service": "columbia-automation",
     ...
   }
   ```

4. **Update Test File:**
   - Open `test_railway.py`
   - Update `RAILWAY_URL` with your actual Railway URL (no trailing slash)
   - Run: `python test_railway.py`

## Common Mistakes

❌ **Wrong:**
- URL with trailing slash: `https://app.up.railway.app/`
- Not generating public domain in Railway
- Using localhost URL: `http://localhost:8080`
- Setting `PORT` environment variable manually (Railway sets it)

✅ **Correct:**
- URL without trailing slash: `https://app.up.railway.app`
- Public domain generated in Railway Settings
- Using Railway public URL
- Letting Railway set `PORT` automatically

## Still Having Issues?

1. **Check Railway Status Page:**
   - https://status.railway.app/
   - See if Railway services are down

2. **Verify Build Succeeded:**
   - Railway Dashboard → Deployments
   - Check build logs for errors
   - Ensure Docker build completed successfully

3. **Test Locally First:**
   - Run `python test_local.py` to verify code works
   - Then test Railway with `python test_railway.py`

4. **Check Railway Documentation:**
   - https://docs.railway.app/

