"""
Test API Trigger Endpoints

Tests all workflow trigger endpoints to verify they correctly publish
messages to Pub/Sub that can be received by the orchestrator.
"""

import requests
import json
from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials
import os
import time

# Configure
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
API_URL = "http://localhost:8000"
PROJECT_ID = "aura-project"

def pull_messages(topic_name: str, count: int = 1) -> list:
    """Pull messages from a subscription."""
    subscriber = pubsub_v1.SubscriberClient(credentials=AnonymousCredentials())
    subscription_path = f"projects/{PROJECT_ID}/subscriptions/{topic_name}-test-sub"
    
    try:
        response = subscriber.pull(
            request={"subscription": subscription_path, "max_messages": count},
            timeout=5.0
        )
        
        messages = []
        for received_message in response.received_messages:
            data = json.loads(received_message.message.data.decode("utf-8"))
            messages.append(data)
            
            # Acknowledge
            subscriber.acknowledge(
                request={
                    "subscription": subscription_path,
                    "ack_ids": [received_message.ack_id]
                }
            )
        
        return messages
    except Exception as e:
        print(f"    Error pulling messages: {e}")
        return []

def test_all_workflows():
    """Test all 5 workflow trigger endpoints."""
    
    print("=" * 70)
    print("TESTING API WORKFLOW TRIGGER ENDPOINTS")
    print("=" * 70)
    print()
    
    # Test cases
    tests = [
        {
            "name": "Workflow 1 - Automatic Execution",
            "endpoint": "/trigger/workflow1",
            "payload": {"underwriting_id": "uw_test_001"},
            "topic": "underwriting.updated",
            "expected_data": {"underwriting_id": "uw_test_001"}
        },
        {
            "name": "Workflow 2 - Manual Execution",
            "endpoint": "/trigger/workflow2",
            "payload": {
                "underwriting_processor_id": "uwp_test_001",
                "execution_id": "exec_001",
                "duplicate": False
            },
            "topic": "underwriting.processor.execute",
            "expected_data": {
                "underwriting_processor_id": "uwp_test_001",
                "execution_id": "exec_001",
                "duplicate": False
            }
        },
        {
            "name": "Workflow 3 - Consolidation Only",
            "endpoint": "/trigger/workflow3",
            "payload": {"underwriting_processor_id": "uwp_test_001"},
            "topic": "underwriting.processor.consolidation",
            "expected_data": {"underwriting_processor_id": "uwp_test_001"}
        },
        {
            "name": "Workflow 4 - Execution Activation",
            "endpoint": "/trigger/workflow4",
            "payload": {"execution_id": "exec_test_001"},
            "topic": "underwriting.execution.activate",
            "expected_data": {"execution_id": "exec_test_001"}
        },
        {
            "name": "Workflow 5 - Execution Deactivation",
            "endpoint": "/trigger/workflow5",
            "payload": {"execution_id": "exec_test_001"},
            "topic": "underwriting.execution.disable",
            "expected_data": {"execution_id": "exec_test_001"}
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"Testing: {test['name']}")
        print("-" * 70)
        print(f"  Endpoint: POST {test['endpoint']}")
        print(f"  Payload: {test['payload']}")
        
        # Call API endpoint
        try:
            response = requests.post(
                f"{API_URL}{test['endpoint']}",
                json=test['payload']
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ API Response: {result['workflow']}")
                print(f"    Message ID: {result['message_id']}")
                
                # Verify message in Pub/Sub
                print(f"  Verifying Pub/Sub message...")
                time.sleep(0.5)  # Short wait
                
                messages = pull_messages(test['topic'], count=1)
                
                if messages and messages[0] == test['expected_data']:
                    print(f"  ✅ Message received correctly in Pub/Sub")
                    print(f"    Data: {messages[0]}")
                    results.append({"test": test['name'], "status": "PASS"})
                elif messages:
                    print(f"  ⚠️  Message data mismatch")
                    print(f"    Expected: {test['expected_data']}")
                    print(f"    Got: {messages[0]}")
                    results.append({"test": test['name'], "status": "FAIL"})
                else:
                    print(f"  ⚠️  No message in subscription")
                    results.append({"test": test['name'], "status": "FAIL"})
            else:
                print(f"  ❌ API Error: {response.status_code}")
                print(f"    {response.text}")
                results.append({"test": test['name'], "status": "FAIL"})
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({"test": test['name'], "status": "FAIL"})
        
        print()
    
    # Print summary
    print("=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print()
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    
    for result in results:
        status_symbol = "✅" if result["status"] == "PASS" else "❌"
        print(f"{status_symbol} {result['test']}: {result['status']}")
    
    print()
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = test_all_workflows()
    exit(0 if success else 1)

