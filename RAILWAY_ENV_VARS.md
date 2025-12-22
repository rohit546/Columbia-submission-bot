# Railway Environment Variables

## Required Variables (Must Add)

Add these in Railway → Variables tab:

```
COLUMBIA_USERNAME=agt41297
COLUMBIA_PASSWORD=Columbia41297
BROWSER_HEADLESS=true
```

## Optional Variables (Have Defaults)

These are optional but can be customized:

```
MAX_WORKERS=3
ENABLE_TRACING=true
CLEANUP_LOGS_DAYS=7
CLEANUP_TRACES_DAYS=30
CLEANUP_SESSIONS_DAYS=7
BROWSER_TIMEOUT=60000
```

## Variables NOT to Set

**DO NOT SET THESE** - Railway handles them automatically:
- `PORT` - Railway automatically provides this
- `WEBHOOK_HOST` - Defaults to `0.0.0.0` (correct for Railway)
- `WEBHOOK_PATH` - Defaults to `/webhook` (correct)
- `COLUMBIA_LOGIN_URL` - Has default value
- `COLUMBIA_QUOTE_URL` - Has default value

## Quick Copy-Paste for Railway

Copy this into Railway Variables (one per line):

```
COLUMBIA_USERNAME=agt41297
COLUMBIA_PASSWORD=Columbia41297
BROWSER_HEADLESS=true
MAX_WORKERS=3
ENABLE_TRACING=true
```

## Variable Descriptions

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `COLUMBIA_USERNAME` | ✅ Yes | `agt41297` | Columbia portal username |
| `COLUMBIA_PASSWORD` | ✅ Yes | `Columbia41297` | Columbia portal password |
| `BROWSER_HEADLESS` | ✅ Yes | `true` | Set to `true` for Railway (Linux) |
| `MAX_WORKERS` | ❌ No | `3` | Number of concurrent automation tasks |
| `ENABLE_TRACING` | ❌ No | `true` | Enable Playwright tracing for debugging |
| `CLEANUP_LOGS_DAYS` | ❌ No | `7` | Days to keep log files |
| `CLEANUP_TRACES_DAYS` | ❌ No | `30` | Days to keep trace files |
| `CLEANUP_SESSIONS_DAYS` | ❌ No | `7` | Days to keep browser sessions |
| `BROWSER_TIMEOUT` | ❌ No | `60000` | Browser timeout in milliseconds |

## How to Add in Railway

1. Go to your Railway project dashboard
2. Click on **Variables** tab
3. Click **+ New Variable** for each variable
4. Enter the **Variable Name** and **Value**
5. Click **Add** to save
6. Railway will automatically redeploy with new variables

## Example Railway Variables Screen

```
Variable Name              Value
─────────────────────────────────────────────
COLUMBIA_USERNAME         agt41297
COLUMBIA_PASSWORD         Columbia41297
BROWSER_HEADLESS          true
MAX_WORKERS               3
ENABLE_TRACING            true
```

## Notes

- **PORT**: Railway automatically sets this - don't add it manually
- **BROWSER_HEADLESS**: Must be `true` on Railway (Linux environment)
- All variables are case-sensitive
- Changes to variables trigger automatic redeployment
- Use Railway's **Secret** option for sensitive values (passwords)

