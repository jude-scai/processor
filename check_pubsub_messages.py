"""
Check Pub/Sub Messages

Tool to verify messages in Pub/Sub topics/subscriptions.
"""

import os
from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials
import json

# Configure Pub/Sub emulator
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
PROJECT_ID = "aura-project"

def check_all_topics():
    """Check messages in all workflow topics."""
    
    print("=" * 70)
    print("CHECKING PUB/SUB MESSAGES")
    print("=" * 70)
    print()
    
    subscriber = pubsub_v1.SubscriberClient(credentials=AnonymousCredentials())
    
    topics = [
        "underwriting.updated",
        "underwriting.processor.execute",
        "underwriting.processor.consolidation",
        "underwriting.execution.activate",
        "underwriting.execution.disable"
    ]
    
    for topic_name in topics:
        subscription_path = f"projects/{PROJECT_ID}/subscriptions/{topic_name}-test-sub"
        
        print(f"Topic: {topic_name}")
        print("-" * 70)
        
        try:
            # Pull messages without acknowledging (peek)
            response = subscriber.pull(
                request={
                    "subscription": subscription_path,
                    "max_messages": 10,
                },
                timeout=2.0
            )
            
            if response.received_messages:
                print(f"  ✅ {len(response.received_messages)} message(s) in queue")
                
                for idx, received_message in enumerate(response.received_messages, 1):
                    message_data = json.loads(received_message.message.data.decode("utf-8"))
                    message_id = received_message.message.message_id
                    print(f"    Message {idx}:")
                    print(f"      ID: {message_id}")
                    print(f"      Data: {message_data}")
                
                # Don't acknowledge - just checking
                # To consume messages, call acknowledge()
            else:
                print(f"  ℹ️  No messages in queue")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()

if __name__ == "__main__":
    check_all_topics()

