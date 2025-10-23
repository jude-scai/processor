"""
Real-time Pub/Sub Message Monitor

Listens for messages on all workflow topics and displays them in real-time.
Press Ctrl+C to stop.
"""

import os
from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials
import json
from datetime import datetime
import time
import threading

# Configure Pub/Sub emulator
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
PROJECT_ID = "aura-project"


class PubSubMonitor:
    """Monitor for Pub/Sub messages."""

    def __init__(self):
        self.subscriber = pubsub_v1.SubscriberClient(credentials=AnonymousCredentials())
        self.running = True
        self.message_count = 0

    def callback(self, message, topic_name):
        """Callback when message is received."""
        self.message_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            data = json.loads(message.data.decode("utf-8"))

            print(f"\n[{timestamp}] 📨 Message #{self.message_count} received!")
            print(f"  Topic: {topic_name}")
            print(f"  Message ID: {message.message_id}")
            print(f"  Data: {json.dumps(data, indent=4)}")
            print("-" * 70)

            # Acknowledge the message
            message.ack()

        except Exception as e:
            print(f"  ❌ Error processing message: {e}")
            message.nack()

    def monitor_topic(self, topic_name):
        """Monitor a specific topic."""
        subscription_path = f"projects/{PROJECT_ID}/subscriptions/{topic_name}-monitor"
        topic_path = f"projects/{PROJECT_ID}/topics/{topic_name}"

        # Create subscription if it doesn't exist
        try:
            self.subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60,
                }
            )
        except:
            pass  # Subscription already exists

        # Subscribe
        future = self.subscriber.subscribe(
            subscription_path,
            callback=lambda message: self.callback(message, topic_name),
        )

        return future

    def start(self):
        """Start monitoring all topics."""
        topics = [
            "underwriting.updated",
            "underwriting.processor.execute",
            "underwriting.processor.consolidation",
            "underwriting.execution.activate",
            "underwriting.execution.disable",
        ]

        print("=" * 70)
        print("PUB/SUB REAL-TIME MONITOR")
        print("=" * 70)
        print()
        print("Listening for messages on topics:")
        for topic in topics:
            print(f"  • {topic}")
        print()
        print("Press Ctrl+C to stop monitoring...")
        print("=" * 70)

        # Start monitoring each topic
        futures = []
        for topic_name in topics:
            future = self.monitor_topic(topic_name)
            futures.append(future)

        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping monitor...")
            for future in futures:
                future.cancel()
            print(f"\n✅ Received {self.message_count} total messages")
            print("Monitor stopped.")


if __name__ == "__main__":
    monitor = PubSubMonitor()
    monitor.start()
