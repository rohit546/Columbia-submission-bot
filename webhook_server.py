"""
Webhook server for Columbia Insurance automation
Receives data from Next.js app and triggers Columbia automation
"""
import asyncio
import json
import logging
import threading
import queue
import time
import shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from columbia_automation import ColumbiaAutomation
from config import (
    WEBHOOK_HOST, WEBHOOK_PORT, WEBHOOK_PATH, LOG_DIR, TRACE_DIR, SESSION_DIR,
    MAX_WORKERS
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'webhook_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS for Next.js
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Store active sessions
active_sessions = {}

# Queue system
task_queue = queue.Queue()
active_workers = 0
worker_lock = threading.Lock()
queue_position = {}

# Browser lock - only ONE browser at a time
browser_lock = threading.Lock()
browser_in_use = False

# Cleanup scheduler configuration
CLEANUP_INTERVAL_HOURS = 6  # Run cleanup every 6 hours
CLEANUP_MAX_AGE_DAYS = 2  # Delete files older than 2 days
MAX_TRACE_FILES = 5  # Keep only last 5 trace files

# Cleanup scheduler thread
cleanup_thread = None
cleanup_stop_event = threading.Event()


def cleanup_old_files():
    """
    Cleanup old files to prevent disk space issues:
    - Delete browser_data folders older than CLEANUP_MAX_AGE_DAYS
    - Keep only MAX_TRACE_FILES most recent trace files
    - Delete old log files older than CLEANUP_MAX_AGE_DAYS
    - Delete all screenshot folders
    """
    logger.info("[CLEANUP] Starting scheduled cleanup...")
    now = time.time()
    max_age_seconds = CLEANUP_MAX_AGE_DAYS * 24 * 60 * 60
    deleted_count = 0
    
    try:
        # 1. Cleanup old browser_data folders (except browser_data_default)
        logger.info("[CLEANUP] Cleaning up old browser_data folders...")
        for folder in SESSION_DIR.glob("browser_data_*"):
            if folder.name == "browser_data_default":
                continue  # Keep the default browser data folder
            try:
                folder_age = now - folder.stat().st_mtime
                if folder_age > max_age_seconds:
                    shutil.rmtree(folder)
                    deleted_count += 1
                    logger.info(f"[CLEANUP] Deleted old browser_data: {folder.name}")
            except Exception as e:
                logger.debug(f"[CLEANUP] Could not delete {folder}: {e}")
        
        # 2. Keep only last MAX_TRACE_FILES trace files
        logger.info("[CLEANUP] Cleaning up old trace files...")
        trace_files = sorted(TRACE_DIR.glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True)
        if len(trace_files) > MAX_TRACE_FILES:
            for trace_file in trace_files[MAX_TRACE_FILES:]:
                try:
                    trace_file.unlink()
                    deleted_count += 1
                    logger.info(f"[CLEANUP] Deleted old trace: {trace_file.name}")
                except Exception as e:
                    logger.debug(f"[CLEANUP] Could not delete trace {trace_file}: {e}")
        
        # 3. Cleanup old log files
        logger.info("[CLEANUP] Cleaning up old log files...")
        for log_file in LOG_DIR.glob("*.log"):
            if log_file.name == "webhook_server.log":
                continue  # Don't delete current log
            try:
                file_age = now - log_file.stat().st_mtime
                if file_age > max_age_seconds:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"[CLEANUP] Deleted old log: {log_file.name}")
            except Exception as e:
                logger.debug(f"[CLEANUP] Could not delete log {log_file}: {e}")
        
        # 4. Delete old screenshot folders
        logger.info("[CLEANUP] Cleaning up screenshot folders...")
        screenshots_dir = LOG_DIR / "screenshots"
        if screenshots_dir.exists():
            for folder in screenshots_dir.iterdir():
                if folder.is_dir():
                    try:
                        folder_age = now - folder.stat().st_mtime
                        if folder_age > max_age_seconds:
                            shutil.rmtree(folder)
                            deleted_count += 1
                            logger.info(f"[CLEANUP] Deleted screenshot folder: {folder.name}")
                    except Exception as e:
                        logger.debug(f"[CLEANUP] Could not delete screenshot folder {folder}: {e}")
        
        logger.info(f"[CLEANUP] Cleanup completed. Deleted {deleted_count} items.")
        
    except Exception as e:
        logger.error(f"[CLEANUP] Error during cleanup: {e}")


def cleanup_scheduler():
    """Background thread that runs cleanup periodically"""
    logger.info(f"[CLEANUP] Scheduler started - will run every {CLEANUP_INTERVAL_HOURS} hours")
    
    while not cleanup_stop_event.is_set():
        # Wait for interval (check stop event every minute)
        for _ in range(CLEANUP_INTERVAL_HOURS * 60):
            if cleanup_stop_event.is_set():
                break
            time.sleep(60)  # Sleep 1 minute at a time
        
        if not cleanup_stop_event.is_set():
            cleanup_old_files()
    
    logger.info("[CLEANUP] Scheduler stopped")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "columbia-automation",
        "timestamp": datetime.now().isoformat(),
        "active_workers": active_workers,
        "max_workers": MAX_WORKERS,
        "queue_size": task_queue.qsize()
    }), 200


@app.route(WEBHOOK_PATH, methods=['POST', 'OPTIONS'])
def webhook_receiver():
    """
    Main webhook endpoint for Columbia automation
    
    Expected payload:
    {
        "action": "start_automation",
        "task_id": "optional_unique_id",
        "quote_data": {
            // Required fields:
            "person_entering_risk": "John Doe",  // or "contact_name"
            "person_entering_risk_email": "john.doe@example.com",  // or "email"
            "company_name": "Test Company LLC",  // or "business_name"
            "mailing_address": "280 Griffin Street, McDonough, GA 30253",  // or "address"
            
            // Optional fields (have defaults):
            "dba": "Test DBA",  // or "dba_name" - optional
            "effective_date": "12/20/2025",  // optional - auto-calculated if not provided
            "business_type": "LIMITED LIABILITY COMPANY",  // optional - defaults to "LIMITED LIABILITY COMPANY"
            "applicant_is": "tenant",  // or "applicant_type" - optional - defaults to "tenant" ("tenant" or "owner")
            "gross_sales": "100000",  // or "gross_sales_amount" - optional - defaults to "100000"
            "construction_year": "2005",  // or "original_construction_year" - optional - auto-calculated if not provided
            "number_of_stories": "1",  // or "stories" - optional - defaults to "1"
            "square_footage": "3500",  // or "square_feet" - optional - defaults to "3500"
            "building_limit": "500000",  // or "building_value" - optional - defaults to "500000" (only used if applicant_is is "owner")
            "bpp_limit": "70000"  // or "business_personal_property_limit" - optional - defaults to "70000"
        }
    }
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    
    try:
        # Get JSON payload
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 400
        
        payload = request.get_json()
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No payload received"
            }), 400
        
        logger.info(f"[COLUMBIA] Webhook request received: {list(payload.keys())}")
        
        # Extract data
        action = payload.get('action', 'start_automation')
        quote_data = payload.get('quote_data', {})
        
        # Validate required fields
        required_fields = []
        missing_fields = []
        
        # Check for person_entering_risk (or contact_name)
        if not quote_data.get('person_entering_risk') and not quote_data.get('contact_name'):
            missing_fields.append('person_entering_risk (or contact_name)')
        else:
            # Normalize to person_entering_risk
            if quote_data.get('contact_name') and not quote_data.get('person_entering_risk'):
                quote_data['person_entering_risk'] = quote_data.pop('contact_name')
        
        # Check for person_entering_risk_email (or email)
        if not quote_data.get('person_entering_risk_email') and not quote_data.get('email'):
            missing_fields.append('person_entering_risk_email (or email)')
        else:
            # Normalize to person_entering_risk_email
            if quote_data.get('email') and not quote_data.get('person_entering_risk_email'):
                quote_data['person_entering_risk_email'] = quote_data.pop('email')
        
        # Check for company_name (or business_name)
        if not quote_data.get('company_name') and not quote_data.get('business_name'):
            missing_fields.append('company_name (or business_name)')
        else:
            # Normalize to company_name
            if quote_data.get('business_name') and not quote_data.get('company_name'):
                quote_data['company_name'] = quote_data.pop('business_name')
        
        # Check for mailing_address (or address)
        if not quote_data.get('mailing_address') and not quote_data.get('address'):
            missing_fields.append('mailing_address (or address)')
        else:
            # Normalize to mailing_address
            if quote_data.get('address') and not quote_data.get('mailing_address'):
                quote_data['mailing_address'] = quote_data.pop('address')
        
        # Return error if required fields are missing
        if missing_fields:
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "missing_fields": missing_fields
            }), 400
        
        # Normalize optional field aliases
        # dba_name -> dba
        if quote_data.get('dba_name') and not quote_data.get('dba'):
            quote_data['dba'] = quote_data.pop('dba_name')
        
        # gross_sales_amount -> gross_sales
        if quote_data.get('gross_sales_amount') and not quote_data.get('gross_sales'):
            quote_data['gross_sales'] = quote_data.pop('gross_sales_amount')
        
        # original_construction_year -> construction_year
        if quote_data.get('original_construction_year') and not quote_data.get('construction_year'):
            quote_data['construction_year'] = quote_data.pop('original_construction_year')
        
        # stories -> number_of_stories
        if quote_data.get('stories') and not quote_data.get('number_of_stories'):
            quote_data['number_of_stories'] = quote_data.pop('stories')
        
        # square_feet -> square_footage
        if quote_data.get('square_feet') and not quote_data.get('square_footage'):
            quote_data['square_footage'] = quote_data.pop('square_feet')
        
        # building_value -> building_limit
        if quote_data.get('building_value') and not quote_data.get('building_limit'):
            quote_data['building_limit'] = quote_data.pop('building_value')
        
        # business_personal_property_limit -> bpp_limit
        if quote_data.get('business_personal_property_limit') and not quote_data.get('bpp_limit'):
            quote_data['bpp_limit'] = quote_data.pop('business_personal_property_limit')
        
        # applicant_type -> applicant_is
        if quote_data.get('applicant_type') and not quote_data.get('applicant_is'):
            quote_data['applicant_is'] = quote_data.pop('applicant_type')
        
        logger.info(f"[COLUMBIA] Validated quote data: {list(quote_data.keys())}")
        
        if action == 'start_automation':
            # Generate task_id
            task_id = payload.get('task_id') or f"columbia_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"[COLUMBIA] Starting automation task: {task_id}")
            logger.info(f"[COLUMBIA] Quote Data: {quote_data}")
            
            # Check worker availability
            with worker_lock:
                current_workers = active_workers
                queue_size = task_queue.qsize()
            
            # Initialize task status
            active_sessions[task_id] = {
                "status": "queued" if current_workers >= MAX_WORKERS else "running",
                "task_id": task_id,
                "queued_at": datetime.now().isoformat(),
                "quote_data": quote_data,
                "queue_position": queue_size + 1 if current_workers >= MAX_WORKERS else 0,
                "active_workers": current_workers,
                "max_workers": MAX_WORKERS
            }
            
            # Add to queue
            task_queue.put((task_id, quote_data))
            
            if current_workers >= MAX_WORKERS:
                logger.info(f"[COLUMBIA] Task {task_id} queued at position {queue_size + 1}")
            else:
                logger.info(f"[COLUMBIA] Task {task_id} will start immediately")
            
            return jsonify({
                "status": "accepted",
                "task_id": task_id,
                "message": "Columbia automation task started",
                "status_url": f"/task/{task_id}/status"
            }), 202
        
        return jsonify({
            "status": "error",
            "message": f"Unknown action: {action}"
        }), 400
        
    except Exception as e:
        logger.error(f"[COLUMBIA] Webhook error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }), 500


@app.route('/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id: str):
    """Get status of an automation task"""
    if task_id in active_sessions:
        return jsonify(active_sessions[task_id]), 200
    else:
        return jsonify({
            "status": "error",
            "message": f"Task {task_id} not found"
        }), 404


@app.route('/tasks', methods=['GET'])
def list_tasks():
    """List all tasks"""
    return jsonify({
        "tasks": list(active_sessions.values()),
        "total": len(active_sessions),
        "active_workers": active_workers,
        "max_workers": MAX_WORKERS,
        "queue_size": task_queue.qsize()
    }), 200


@app.route('/queue/status', methods=['GET'])
def queue_status():
    """Get queue status"""
    return jsonify({
        "queue_size": task_queue.qsize(),
        "active_workers": active_workers,
        "max_workers": MAX_WORKERS,
        "browser_in_use": browser_in_use
    }), 200


@app.route('/trace/<task_id>', methods=['GET'])
def get_trace(task_id: str):
    """
    Download trace file for a specific task or company name
    Supports:
    - Task ID: /trace/columbia_20231222_123456
    - Company name (sanitized): /trace/test_company_llc
    - Company name (original): Will be sanitized automatically
    """
    try:
        # Sanitize task_id if it looks like a company name (contains spaces or special chars)
        # If it's already sanitized (no spaces, lowercase), use as-is
        sanitized_id = task_id.lower()
        if any(c in task_id for c in [' ', '.', ',', '&', '-', '@']):
            # Contains special chars, sanitize it
            sanitized_id = "".join(c if c.isalnum() or c == '_' else "_" for c in task_id)[:30].lower()
        
        # Try multiple trace file patterns (like Guard)
        trace_candidates = [
            TRACE_DIR / f"{sanitized_id}.zip",  # Sanitized company name
            TRACE_DIR / f"{task_id}.zip",  # Original task_id
            TRACE_DIR / f"default.zip",  # Default trace
            *list(TRACE_DIR.glob(f"*{sanitized_id}*.zip")),  # Any file containing sanitized_id
            *list(TRACE_DIR.glob(f"*{task_id}*.zip")),  # Any file containing task_id
        ]
        
        # Find the first existing trace file
        trace_path = None
        for candidate in trace_candidates:
            if candidate.exists() and candidate.is_file():
                trace_path = candidate
                break
        
        if not trace_path:
            logger.warning(f"Trace not found for: {task_id} (sanitized: {sanitized_id})")
            logger.info(f"Searched paths: {[str(p) for p in trace_candidates[:5]]}")
            return jsonify({
                "status": "not_found",
                "message": f"Trace not found for {task_id}",
                "searched": sanitized_id
            }), 404
        
        logger.info(f"Serving trace for {task_id}: {trace_path}")
        return send_file(
            str(trace_path),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{trace_path.name}"
        )
    except Exception as e:
        logger.error(f"Error serving trace for {task_id}: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/traces', methods=['GET'])
def list_traces():
    """List all available trace files - returns HTML UI or JSON"""
    try:
        traces = []
        for trace_file in sorted(TRACE_DIR.glob("*.zip"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                stat = trace_file.stat()
                traces.append({
                    "task_id": trace_file.stem,
                    "filename": trace_file.name,
                    "size_bytes": stat.st_size,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "url": f"/trace/{trace_file.stem}"
                })
            except Exception as e:
                logger.debug(f"Error getting info for {trace_file}: {e}")
        
        # Return HTML if browser request, JSON otherwise
        if 'text/html' in request.headers.get('Accept', '') or request.args.get('format') != 'json':
            html = '''<!DOCTYPE html>
<html><head><title>Columbia Automation - Traces</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Arial,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#f5f5f5}
h1{color:#2c3e50;border-bottom:3px solid #3498db;padding-bottom:10px;margin-bottom:20px}
.info{background:#e8f4f8;padding:15px;border-radius:8px;margin-bottom:20px;line-height:1.6}
table{width:100%;border-collapse:collapse;background:white;box-shadow:0 2px 5px rgba(0,0,0,0.1);border-radius:8px;overflow:hidden;margin-bottom:20px}
th{background:#3498db;color:white;padding:12px;text-align:left;font-weight:600}
td{padding:12px;text-align:left;border-bottom:1px solid #eee}
tr:hover{background:#f8f9fa}
tr:last-child td{border-bottom:none}
code{background:#f1f2f6;padding:2px 6px;border-radius:3px;font-family:'Courier New',monospace;font-size:0.9em}
.size{color:#7f8c8d;font-weight:500}
.date{color:#95a5a6;font-size:0.9em}
.download-btn{background:#27ae60;color:white;padding:8px 16px;border-radius:4px;font-size:0.9em;text-decoration:none;display:inline-block;transition:background 0.2s}
.download-btn:hover{background:#219a52;text-decoration:none}
.empty{text-align:center;padding:40px;color:#7f8c8d;background:white;border-radius:8px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}
.empty-icon{font-size:48px;margin-bottom:15px}
.footer{margin-top:30px;text-align:center;color:#95a5a6;font-size:0.85em}
.footer a{color:#3498db;text-decoration:none;margin:0 10px}
.footer a:hover{text-decoration:underline}
</style></head>
<body>
<h1>🎯 Columbia Automation - Traces</h1>
<div class="info">
<strong>Total:</strong> ''' + str(len(traces)) + ''' traces | <strong>Max stored:</strong> ''' + str(MAX_TRACE_FILES) + '''<br>
<small>Trace files are named by company name. Only the most recent ''' + str(MAX_TRACE_FILES) + ''' traces are kept.</small>
</div>'''
            
            if traces:
                html += '''<table>
<tr><th>Company Name / Trace ID</th><th>Size</th><th>Created</th><th>Action</th></tr>'''
                for t in traces:
                    html += f'''<tr>
<td><code>{t["task_id"]}</code></td>
<td class="size">{t["size_kb"]} KB</td>
<td class="date">{t["created_at"][:19].replace('T', ' ')}</td>
<td><a href="{t["url"]}" class="download-btn">⬇ Download</a></td>
</tr>'''
                html += '</table>'
            else:
                html += '''<div class="empty">
<div class="empty-icon">📭</div>
<strong>No traces available yet.</strong><br>
Run an automation task to generate trace files.
</div>'''
            
            html += '''
<div class="footer">
Columbia Insurance Automation Server | <a href="/health">Health Check</a> | <a href="/tasks">Tasks</a> | <a href="/traces?format=json">JSON API</a>
</div>
</body></html>'''
            return html, 200, {'Content-Type': 'text/html'}
        
        return jsonify({
            "total": len(traces),
            "max_traces": MAX_TRACE_FILES,
            "traces": traces
        }), 200
    except Exception as e:
        logger.error(f"Error listing traces: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def run_automation_task_sync(task_id: str, quote_data: dict):
    """Run automation task synchronously in a thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_automation_task(task_id, quote_data))
    finally:
        loop.close()


async def run_automation_task(task_id: str, quote_data: dict):
    """Run Columbia automation task asynchronously"""
    global active_workers, browser_in_use
    
    logger.info(f"[TASK {task_id}] Starting Columbia automation")
    logger.info(f"[TASK {task_id}] Quote Data: {json.dumps(quote_data, indent=2)}")
    
    # Create trace_id from company name if available
    trace_id = None
    if quote_data and quote_data.get('company_name'):
        company_name = quote_data.get('company_name', '')
        # Sanitize company name for filename (remove special chars, limit length)
        safe_company = "".join(c if c.isalnum() else "_" for c in company_name)[:30].lower()
        trace_id = safe_company
        logger.info(f"[TASK {task_id}] Trace ID from company name: {trace_id}")
    
    # Fallback to task_id if no company name
    if not trace_id:
        trace_id = f"columbia_{task_id}"
        logger.info(f"[TASK {task_id}] Trace ID from task_id: {trace_id}")
    
    try:
        # Update status to running
        if task_id in active_sessions:
            active_sessions[task_id]["status"] = "running"
            active_sessions[task_id]["started_at"] = datetime.now().isoformat()
        
        # Initialize automation handler
        automation = ColumbiaAutomation(
            task_id="default",  # Use default session
            trace_id=trace_id,
            **quote_data
        )
        
        # Run complete automation flow
        await automation.run()
        
        # Update status to completed
        if task_id in active_sessions:
            active_sessions[task_id]["status"] = "completed"
            active_sessions[task_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"[TASK {task_id}] ✅ Automation completed successfully")
        
    except Exception as e:
        logger.error(f"[TASK {task_id}] ❌ Automation failed: {e}", exc_info=True)
        if task_id in active_sessions:
            active_sessions[task_id]["status"] = "failed"
            active_sessions[task_id]["error"] = str(e)
            active_sessions[task_id]["failed_at"] = datetime.now().isoformat()
    finally:
        # Cleanup (already handled in run())
        pass
        
        # Release worker slot
        with worker_lock:
            active_workers -= 1
            browser_in_use = False
        
        logger.info(f"[TASK {task_id}] Worker released. Active workers: {active_workers}")


def worker_thread():
    """Worker thread that processes tasks from the queue"""
    global active_workers, browser_in_use
    
    logger.info("[WORKER] Worker thread started")
    
    while True:
        try:
            # Get task from queue
            task_id, quote_data = task_queue.get(timeout=1)
            
            # Acquire worker slot
            with worker_lock:
                if active_workers >= MAX_WORKERS:
                    logger.warning(f"[WORKER] Max workers reached, requeuing task {task_id}")
                    task_queue.put((task_id, quote_data))
                    continue
                
                active_workers += 1
                browser_in_use = True
            
            logger.info(f"[WORKER] Processing task {task_id} (Workers: {active_workers}/{MAX_WORKERS})")
            
            # Run automation task
            run_automation_task_sync(task_id, quote_data)
            
            # Mark task as done
            task_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"[WORKER] Error in worker thread: {e}", exc_info=True)
            with worker_lock:
                active_workers -= 1
                browser_in_use = False


if __name__ == '__main__':
    # Start cleanup scheduler
    cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
    cleanup_thread.start()
    logger.info("[SERVER] Cleanup scheduler started")
    
    # Start worker threads
    for i in range(MAX_WORKERS):
        worker = threading.Thread(target=worker_thread, daemon=True)
        worker.start()
        logger.info(f"[SERVER] Worker thread {i+1} started")
    
    logger.info(f"[SERVER] Columbia Automation Webhook Server starting on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
    logger.info(f"[SERVER] Webhook path: {WEBHOOK_PATH}")
    logger.info(f"[SERVER] Max workers: {MAX_WORKERS}")
    
    # Run Flask app
    app.run(host=WEBHOOK_HOST, port=WEBHOOK_PORT, debug=False, threaded=True)

