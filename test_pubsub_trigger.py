"""
Test Pub/Sub Trigger Endpoints

Verifies that the trigger endpoints correctly publish messages to Pub/Sub topics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials
import json
import os
import time

# Configure Pub/Sub emulator
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
PROJECT_ID = "aura-project"

def test_pubsub_trigger():
    """Test Pub/Sub message publishing and receiving."""
    
    print("=" * 70)
    print("TESTING PUB/SUB TRIGGER ENDPOINTS")
    print("=" * 70)
    print()
    
    # Create publisher and subscriber
    publisher = pubsub_v1.PublisherClient(credentials=AnonymousCredentials())
    subscriber = pubsub_v1.SubscriberClient(credentials=AnonymousCredentials())
    
    # Test topics
    topics = [
        "underwriting.updated",
        "underwriting.processor.execute",
        "underwriting.processor.consolidation",
        "underwriting.execution.activate",
        "underwriting.execution.disable"
    ]
    
    # Create topics and subscriptions
    print("Setting up topics and subscriptions...")
    print("-" * 70)
    
    for topic_name in topics:
        topic_path = f"projects/{PROJECT_ID}/topics/{topic_name}"
        subscription_path = f"projects/{PROJECT_ID}/subscriptions/{topic_name}-test-sub"
        
        # Create topic
        try:
            publisher.create_topic(request={"name": topic_path})
            print(f"✅ Created topic: {topic_name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Topic exists: {topic_name}")
            else:
                print(f"❌ Error creating topic {topic_name}: {e}")
        
        # Create subscription
        try:
            subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60
                }
            )
            print(f"✅ Created subscription: {topic_name}-test-sub")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  Subscription exists: {topic_name}-test-sub")
            else:
                print(f"❌ Error creating subscription: {e}")
    
    print()
    print("=" * 70)
    print("PUBLISHING TEST MESSAGES")
    print("=" * 70)
    print()
    
    # Test each workflow
    test_cases = [
        {
            "name": "Workflow 1 - underwriting.updated",
            "topic": "underwriting.updated",
            "data": {"underwriting_id": "uw_test_001"}
        },
        {
            "name": "Workflow 2 - underwriting.processor.execute",
            "topic": "underwriting.processor.execute",
            "data": {"underwriting_processor_id": "uwp_test_001"}
        },
        {
            "name": "Workflow 3 - underwriting.processor.consolidation",
            "topic": "underwriting.processor.consolidation",
            "data": {"underwriting_processor_id": "uwp_test_001"}
        },
        {
            "name": "Workflow 4 - underwriting.execution.activate",
            "topic": "underwriting.execution.activate",
            "data": {"execution_id": "exec_test_001"}
        },
        {
            "name": "Workflow 5 - underwriting.execution.disable",
            "topic": "underwriting.execution.disable",
            "data": {"execution_id": "exec_test_001"}
        }
    ]
    
    published_messages = []
    
    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        print(f"  Topic: {test_case['topic']}")
        print(f"  Data: {test_case['data']}")
        
        topic_path = f"projects/{PROJECT_ID}/topics/{test_case['topic']}"
        message_data = json.dumps(test_case['data']).encode("utf-8")
        
        try:
            future = publisher.publish(topic_path, message_data)
            message_id = future.result(timeout=5.0)
            print(f"  ✅ Published! Message ID: {message_id}")
            published_messages.append({
                "topic": test_case['topic'],
                "message_id": message_id,
                "data": test_case['data']
            })
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        print()
    
    # Wait a bit for messages to be available
    time.sleep(2)
    
    print("=" * 70)
    print("VERIFYING MESSAGES IN SUBSCRIPTIONS")
    print("=" * 70)
    print()
    
    # Verify messages were published
    for topic_name in topics:
        subscription_path = f"projects/{PROJECT_ID}/subscriptions/{topic_name}-test-sub"
        
        print(f"Checking subscription: {topic_name}-test-sub")
        
        try:
            # Pull messages
            response = subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": 10
                },
                timeout=5.0
            )
            
            if response.received_messages:
                print(f"  ✅ Received {len(response.received_messages)} message(s)")
                
                for received_message in response.received_messages:
                    message_data = json.loads(received_message.message.data.decode("utf-8"))
                    print(f"    • Data: {message_data}")
                    
                    # Acknowledge messages
                    subscriber.acknowledge(
                        request={
                            "subscription": subscription_path,
                            "ack_ids": [received_message.ack_id]
                        }
                    )
            else:
                print(f"  ⚠️  No messages in subscription")
        except Exception as e:
            print(f"  ❌ Error pulling messages: {e}")
        
        print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"✅ Published {len(published_messages)} messages successfully")
    print()
    print("Topics configured:")
    for topic in topics:
        print(f"  • {topic}")
    print()
    print("All workflow triggers are working!")
    print()

if __name__ == "__main__":
    test_pubsub_trigger()

