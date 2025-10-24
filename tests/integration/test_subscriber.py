"""
Integration Tests for Pub/Sub Subscriber

Tests the subscriber's ability to listen to topics and process messages.
"""

import pytest
import os
import json
import time
from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials

# Configure Pub/Sub emulator
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
PUBSUB_PROJECT = "aura-project"


class TestPubSubSubscriber:
    """Test cases for Pub/Sub subscriber functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test publisher and subscriber."""
        self.publisher = pubsub_v1.PublisherClient(credentials=AnonymousCredentials())
        self.subscriber = pubsub_v1.SubscriberClient(credentials=AnonymousCredentials())
        yield

    def test_topics_exist(self):
        """Test that required topics exist."""
        topics = [
            "underwriting.updated",
            "document.analyzed",
        ]

        for topic_name in topics:
            topic_path = f"projects/{PUBSUB_PROJECT}/topics/{topic_name}"
            try:
                topic = self.publisher.get_topic(request={"topic": topic_path})
                assert topic is not None
                assert topic.name == topic_path
            except Exception as e:
                pytest.fail(f"Topic {topic_name} does not exist: {e}")

    def test_subscriptions_exist(self):
        """Test that orchestrator subscriptions exist."""
        subscriptions = [
            "underwriting.updated-orchestrator-sub",
            "document.analyzed-orchestrator-sub",
        ]

        for sub_name in subscriptions:
            subscription_path = f"projects/{PUBSUB_PROJECT}/subscriptions/{sub_name}"
            try:
                subscription = self.subscriber.get_subscription(
                    request={"subscription": subscription_path}
                )
                assert subscription is not None
                assert subscription.name == subscription_path
            except Exception as e:
                pytest.fail(f"Subscription {sub_name} does not exist: {e}")

    def test_publish_message(self):
        """Test publishing message to underwriting.updated topic."""
        topic_path = f"projects/{PUBSUB_PROJECT}/topics/underwriting.updated"

        # Publish message
        message_data = json.dumps({"underwriting_id": "test_uw_123"}).encode("utf-8")
        future = self.publisher.publish(topic_path, message_data)
        message_id = future.result(timeout=5)

        assert message_id is not None
        assert isinstance(message_id, str)

    def test_subscription_receives_message(self):
        """Test that subscription can receive published messages."""
        topic_path = f"projects/{PUBSUB_PROJECT}/topics/underwriting.updated"
        subscription_path = f"projects/{PUBSUB_PROJECT}/subscriptions/test-sub-temp"

        # Create temporary subscription for testing
        try:
            self.subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60,
                }
            )
        except Exception:
            pass  # Subscription might already exist

        # Publish message
        test_data = {"underwriting_id": "test_uw_456", "test": True}
        message_data = json.dumps(test_data).encode("utf-8")
        future = self.publisher.publish(topic_path, message_data)
        message_id = future.result(timeout=5)

        # Wait for message to be available
        time.sleep(1)

        # Pull message
        response = self.subscriber.pull(
            request={"subscription": subscription_path, "max_messages": 1}, timeout=5
        )

        # Verify message received
        assert len(response.received_messages) > 0
        received_message = response.received_messages[0]
        received_data = json.loads(received_message.message.data.decode("utf-8"))

        assert received_data == test_data
        assert received_message.message.message_id == message_id

        # Acknowledge message
        self.subscriber.acknowledge(
            request={
                "subscription": subscription_path,
                "ack_ids": [received_message.ack_id],
            }
        )

        # Cleanup
        try:
            self.subscriber.delete_subscription(
                request={"subscription": subscription_path}
            )
        except Exception:
            pass

    def test_multiple_topics_listening(self):
        """Test that subscriber is configured for multiple topics."""
        # This test verifies the topics the subscriber should listen to exist
        required_topics = [
            "underwriting.updated",
            "document.analyzed",
        ]

        for topic_name in required_topics:
            topic_path = f"projects/{PUBSUB_PROJECT}/topics/{topic_name}"
            subscription_path = (
                f"projects/{PUBSUB_PROJECT}/subscriptions/{topic_name}-orchestrator-sub"
            )

            # Verify topic exists
            topic = self.publisher.get_topic(request={"topic": topic_path})
            assert topic is not None

            # Verify subscription exists
            subscription = self.subscriber.get_subscription(
                request={"subscription": subscription_path}
            )
            assert subscription is not None
            assert subscription.topic == topic_path

    def test_message_ack_deadline(self):
        """Test that subscriptions have proper ack deadline configured."""
        subscription_path = f"projects/{PUBSUB_PROJECT}/subscriptions/underwriting.updated-orchestrator-sub"

        subscription = self.subscriber.get_subscription(
            request={"subscription": subscription_path}
        )

        # Verify ack deadline is set (should be 60 seconds)
        assert subscription.ack_deadline_seconds >= 10
        assert subscription.ack_deadline_seconds <= 600
