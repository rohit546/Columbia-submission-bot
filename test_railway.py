"""
Columbia Automation - Railway Deployment Test
==============================================
Tests the Columbia automation webhook on Railway

Usage: python test_railway.py
"""
import requests
import time
import sys
import json
from datetime import datetime, timedelta

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ============================================================================
# CONFIGURATION
# ============================================================================

# Railway Server URL (update this with your Railway URL)
# IMPORTANT: Remove trailing slash, Railway URL should NOT end with /
RAILWAY_URL = "https://columbia-submission-bot-production.up.railway.app"

# Local Server URL (for testing locally)
LOCAL_URL = "http://localhost:5001"

# Choose which server to use
SERVER_URL = RAILWAY_URL  # Change to LOCAL_URL for local testing

# ============================================================================
# TEST DATA
# ============================================================================

def get_full_automation_data():
    """Get full automation data with all fields"""
    effective_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    
    return {
        "action": "start_automation",
        "task_id": f"columbia_railway_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "quote_data": {
            # Required fields
            "person_entering_risk": "John Doe",
            "person_entering_risk_email": "john.doe@example.com",
            "company_name": "Test Company LLC",
            "mailing_address": "280 Griffin Street, McDonough, GA 30253",
            
            # Optional fields
            "dba": "Test DBA",
            "effective_date": effective_date,
            "business_type": "LIMITED LIABILITY COMPANY",
            "applicant_is": "tenant",
            "gross_sales": "100000",
            "construction_year": "2005",
            "number_of_stories": "2",
            "square_footage": "3500",
            "bpp_limit": "70000"
        }
    }

def get_owner_test_data():
    """Get test data for owner (includes building_limit)"""
    effective_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    
    return {
        "action": "start_automation",
        "task_id": f"columbia_owner_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "quote_data": {
            # Required fields
            "person_entering_risk": "Jane Smith",
            "person_entering_risk_email": "jane.smith@example.com",
            "company_name": "Smith Enterprises LLC",
            "mailing_address": "4964 lavista road tucker GA",
            
            # Optional fields
            "dba": "Smith DBA",
            "effective_date": effective_date,
            "business_type": "LIMITED LIABILITY COMPANY",
            "applicant_is": "owner",  # Owner instead of tenant
            "gross_sales": "150000",
            "construction_year": "2010",
            "number_of_stories": "3",
            "square_footage": "4500",
            "building_limit": "600000",  # Required for owner
            "bpp_limit": "80000"
        }
    }

def get_minimal_data():
    """Get minimal data (only required fields)"""
    return {
        "action": "start_automation",
        "task_id": f"columbia_minimal_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "quote_data": {
            # Only required fields
            "person_entering_risk": "Bob Johnson",
            "person_entering_risk_email": "bob.johnson@example.com",
            "company_name": "Johnson Corp",
            "mailing_address": "271 Tuskegee St SE Atlanta GA 30315-1975"
        }
    }

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def check_server_health():
    """Check if server is running"""
    # Remove trailing slash if present
    server_url = SERVER_URL.rstrip('/')
    
    try:
        health_url = f"{server_url}/health"
        print(f"   Checking: {health_url}")
        response = requests.get(health_url, timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Server is healthy")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Active Workers: {health_data.get('active_workers')}/{health_data.get('max_workers')}")
            print(f"   Queue Size: {health_data.get('queue_size')}")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: Cannot reach server")
        print(f"   URL: {server_url}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Check if Railway service is deployed and running")
        print(f"   2. Verify the Railway URL is correct (no trailing slash)")
        print(f"   3. Make sure the service is publicly accessible:")
        print(f"      - Go to Railway dashboard → Your service → Settings → Networking")
        print(f"      - Ensure 'Generate Domain' is enabled")
        print(f"      - Copy the exact public URL (without trailing slash)")
        print(f"   4. Check Railway deployment logs for errors")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ Request Timeout: Server took too long to respond")
        print(f"   URL: {server_url}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   URL: {server_url}")
        print(f"   Make sure the server is running and accessible")
        return False

def test_webhook(payload, test_name="Test"):
    """Test webhook with given payload"""
    # Remove trailing slash if present
    server_url = SERVER_URL.rstrip('/')
    
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)
    
    print(f"\n📤 Sending request to: {server_url}/webhook")
    print(f"   Task ID: {payload.get('task_id')}")
    print(f"   Fields: {list(payload.get('quote_data', {}).keys())}")
    
    try:
        response = requests.post(
            f"{server_url}/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 202:
            response_data = response.json()
            task_id = response_data.get("task_id")
            print(f"✅ Task accepted!")
            print(f"   Task ID: {task_id}")
            print(f"   Status URL: {server_url}/task/{task_id}/status")
            
            # Poll for status
            print(f"\n⏳ Waiting for task to complete (this may take 2-5 minutes)...")
            max_wait = 600  # 10 minutes
            wait_interval = 5  # Check every 5 seconds
            elapsed = 0
            
            while elapsed < max_wait:
                time.sleep(wait_interval)
                elapsed += wait_interval
                
                try:
                    status_response = requests.get(
                        f"{server_url}/task/{task_id}/status",
                        timeout=10
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status")
                        
                        if elapsed % 30 == 0:  # Print every 30 seconds
                            print(f"   [{elapsed}s] Status: {status}")
                        
                        if status == "completed":
                            print(f"\n✅ Task completed successfully!")
                            if "completed_at" in status_data:
                                print(f"   Completed at: {status_data['completed_at']}")
                            return True
                        elif status == "failed":
                            print(f"\n❌ Task failed!")
                            if "error" in status_data:
                                print(f"   Error: {status_data['error']}")
                            return False
                        elif status == "running":
                            continue
                        elif status == "queued":
                            queue_pos = status_data.get("queue_position", 0)
                            if queue_pos > 0:
                                print(f"   [{elapsed}s] Queued at position: {queue_pos}")
                            continue
                except Exception as e:
                    if elapsed % 30 == 0:
                        print(f"   ⚠️ Error checking status: {e}")
                    continue
            
            print(f"\n⏱️ Timeout waiting for task (waited {max_wait}s)")
            return False
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all tests"""
    server_url = SERVER_URL.rstrip('/')
    
    print("\n" + "=" * 80)
    print("COLUMBIA AUTOMATION - RAILWAY DEPLOYMENT TEST")
    print("=" * 80)
    print(f"\nServer URL: {server_url}")
    
    # Check server health
    if not check_server_health():
        print("\n❌ Server health check failed. Exiting.")
        sys.exit(1)
    
    # Test 1: Full automation (tenant)
    print("\n" + "=" * 80)
    payload1 = get_full_automation_data()
    result1 = test_webhook(payload1, "Full Automation (Tenant)")
    
    if result1:
        print("\n✅ Test 1 PASSED")
    else:
        print("\n❌ Test 1 FAILED")
    
    # Wait before next test
    if result1:
        print("\n⏳ Waiting 10 seconds before next test...")
        time.sleep(10)
    
    # Test 2: Owner test
    print("\n" + "=" * 80)
    payload2 = get_owner_test_data()
    result2 = test_webhook(payload2, "Full Automation (Owner)")
    
    if result2:
        print("\n✅ Test 2 PASSED")
    else:
        print("\n❌ Test 2 FAILED")
    
    # Wait before next test
    if result2:
        print("\n⏳ Waiting 10 seconds before next test...")
        time.sleep(10)
    
    # Test 3: Minimal data
    print("\n" + "=" * 80)
    payload3 = get_minimal_data()
    result3 = test_webhook(payload3, "Minimal Data (Required Fields Only)")
    
    if result3:
        print("\n✅ Test 3 PASSED")
    else:
        print("\n❌ Test 3 FAILED")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Full - Tenant): {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"Test 2 (Full - Owner): {'✅ PASSED' if result2 else '❌ FAILED'}")
    print(f"Test 3 (Minimal): {'✅ PASSED' if result3 else '❌ FAILED'}")
    
    all_passed = result1 and result2 and result3
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

