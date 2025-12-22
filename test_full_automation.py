"""
Test script for Columbia automation (full automation test)
Tests the webhook with all user-provided fields
"""
import requests
import json
import sys
import time
from datetime import datetime, timedelta

SERVER_URL = "http://localhost:5001"

def check_server_health():
    """Check if server is running"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_full_automation_data():
    """Get full automation data with all required and optional fields"""
    # Calculate effective date (current + 1 day)
    effective_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    
    return {
        "action": "start_automation",
        "task_id": f"columbia_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "quote_data": {
            # Required fields
            "person_entering_risk": "John Doe",
            "person_entering_risk_email": "john.doe@example.com",
            "company_name": "Test Company LLC",
            "mailing_address": "280 Griffin Street, McDonough, GA 30253",
            
            # Optional fields (with defaults)
            "dba": "Test DBA",
            "effective_date": effective_date,
            "business_type": "LIMITED LIABILITY COMPANY",
            "applicant_is": "tenant",  # or "owner"
            "gross_sales": "100000",
            "construction_year": "2005",
            "number_of_stories": "2",
            "square_footage": "3500",
            "bpp_limit": "70000"
        }
    }

def get_sample_data_2():
    """Get sample data for owner (different applicant type)"""
    effective_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
    
    return {
        "action": "start_automation",
        "task_id": f"columbia_test_owner_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "quote_data": {
            # Required fields
            "person_entering_risk": "Jane Smith",
            "person_entering_risk_email": "jane.smith@example.com",
            "company_name": "Smith Enterprises LLC",
            "mailing_address": "390 Canebrake Rd Savannah GA 31419-9000",
            
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
        "task_id": f"columbia_test_minimal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "quote_data": {
            # Only required fields
            "person_entering_risk": "Bob Johnson",
            "person_entering_risk_email": "bob.johnson@example.com",
            "company_name": "Johnson Corp",
            "mailing_address": "271 Tuskegee St SE Atlanta GA 30315-1975"
        }
    }

def test_columbia_automation(payload, test_name="Full Automation"):
    """Test Columbia automation with given payload"""
    
    print("\n" + "=" * 80)
    print(f"COLUMBIA AUTOMATION TEST: {test_name}")
    print("=" * 80)
    
    # Check server health
    if not check_server_health():
        print("\n❌ Server not available.")
        print("   Start local server: python webhook_server.py")
        return False
    
    print("\n✅ Server is running")
    
    print("\n📤 Sending request...")
    print(f"   URL: {SERVER_URL}/webhook")
    print(f"   Task ID: {payload.get('task_id')}")
    print(f"   Payload fields: {list(payload.get('quote_data', {}).keys())}")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code == 202:
            response_data = response.json()
            task_id = response_data.get("task_id")
            print(f"   Response: {json.dumps(response_data, indent=2)}")
            print(f"\n✅ Task accepted!")
            print(f"   Task ID: {task_id}")
            print(f"   Status URL: {SERVER_URL}/task/{task_id}/status")
            
            # Poll for status
            print("\n⏳ Waiting for task to complete...")
            max_wait = 300  # 5 minutes
            wait_interval = 5  # Check every 5 seconds
            elapsed = 0
            
            while elapsed < max_wait:
                time.sleep(wait_interval)
                elapsed += wait_interval
                
                try:
                    status_response = requests.get(f"{SERVER_URL}/task/{task_id}/status", timeout=10)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get("status")
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
                except Exception as e:
                    print(f"   ⚠️ Error checking status: {e}")
                    continue
            
            print(f"\n⏱️ Timeout waiting for task to complete (waited {max_wait}s)")
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

def main():
    """Run all test cases"""
    print("\n" + "=" * 80)
    print("COLUMBIA AUTOMATION - FULL TEST SUITE")
    print("=" * 80)
    
    # Test 1: Full automation with all fields (tenant)
    print("\n" + "=" * 80)
    print("TEST 1: Full Automation (Tenant)")
    print("=" * 80)
    payload1 = get_full_automation_data()
    result1 = test_columbia_automation(payload1, "Full Automation (Tenant)")
    
    if not result1:
        print("\n⚠️ Test 1 failed, but continuing with other tests...")
    
    # Wait a bit before next test
    time.sleep(5)
    
    # Test 2: Full automation with owner
    print("\n" + "=" * 80)
    print("TEST 2: Full Automation (Owner)")
    print("=" * 80)
    payload2 = get_sample_data_2()
    result2 = test_columbia_automation(payload2, "Full Automation (Owner)")
    
    if not result2:
        print("\n⚠️ Test 2 failed, but continuing with other tests...")
    
    # Wait a bit before next test
    time.sleep(5)
    
    # Test 3: Minimal data (only required fields)
    print("\n" + "=" * 80)
    print("TEST 3: Minimal Data (Required Fields Only)")
    print("=" * 80)
    payload3 = get_minimal_data()
    result3 = test_columbia_automation(payload3, "Minimal Data")
    
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

