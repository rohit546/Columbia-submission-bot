"""
Test script for Columbia automation (local server)
"""
import requests
import json
import sys

SERVER_URL = "http://localhost:5001"

def check_server_health():
    """Check if server is running"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_columbia_automation():
    """Test Columbia automation with sample data"""
    
    print("\n" + "=" * 80)
    print("COLUMBIA AUTOMATION TEST")
    print("=" * 80)
    
    # Check server health
    if not check_server_health():
        print("\n❌ Server not available.")
        print("   Start local server: python webhook_server.py")
        sys.exit(1)
    
    print("\n✅ Server is running")
    
    # Sample quote data with all user-provided fields
    payload = {
        "action": "start_automation",
        "task_id": "test_columbia_001",
        "quote_data": {
            # Required fields
            "person_entering_risk": "John Doe",
            "person_entering_risk_email": "john.doe@example.com",
            "company_name": "Test Company LLC",
            "mailing_address": "280 Griffin Street, McDonough, GA 30253",
            
            # Optional fields (with defaults)
            "dba": "Test DBA",
            "business_type": "LIMITED LIABILITY COMPANY",
            "applicant_is": "tenant",  # or "owner"
            "gross_sales": "100000",
            "construction_year": "2005",
            "number_of_stories": "2",
            "square_footage": "3500",
            "building_limit": "500000",  # Only used if applicant_is is "owner"
            "bpp_limit": "70000"
        }
    }
    
    print("\n📤 Sending request...")
    print(f"   URL: {SERVER_URL}/webhook")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 202:
            task_id = response.json().get("task_id")
            print(f"\n✅ Task accepted!")
            print(f"   Task ID: {task_id}")
            print(f"   Check status: {SERVER_URL}/task/{task_id}/status")
            
            # Poll for status
            print("\n⏳ Waiting for task to complete...")
            import time
            for i in range(60):  # Wait up to 60 seconds
                time.sleep(2)
                status_response = requests.get(f"{SERVER_URL}/task/{task_id}/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status")
                    print(f"   Status: {status}")
                    
                    if status in ["completed", "failed"]:
                        print(f"\n{'✅' if status == 'completed' else '❌'} Task {status}!")
                        print(f"   Full status: {json.dumps(status_data, indent=2)}")
                        break
        else:
            print(f"\n❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_columbia_automation()

