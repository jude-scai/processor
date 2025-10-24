"""
AURA Pub/Sub Subscriber

Listens to Pub/Sub topics and triggers workflow orchestration.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import json
import os
import time
import subprocess
from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials
import psycopg2
from psycopg2.extras import RealDictCursor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.aura.processing_engine.services.orchestrator import create_orchestrator

# Pub/Sub configuration
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
PUBSUB_PROJECT = "aura-project"


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="aura_underwriting",
        user="aura_user",
        password="aura_password",
        cursor_factory=RealDictCursor,
    )


def create_topic_if_not_exists(publisher, topic_path):
    """Create topic if it doesn't exist."""
    try:
        publisher.get_topic(request={"topic": topic_path})
        print(f"✓ Topic exists: {topic_path}", flush=True)
    except Exception:
        try:
            publisher.create_topic(request={"name": topic_path})
            print(f"✓ Created topic: {topic_path}", flush=True)
        except Exception as e:
            print(f"✗ Error creating topic: {e}", flush=True)


def create_subscription_if_not_exists(subscriber, topic_path, subscription_path):
    """Create subscription if it doesn't exist."""
    try:
        subscriber.get_subscription(request={"subscription": subscription_path})
        print(f"✓ Subscription exists: {subscription_path}", flush=True)
    except Exception:
        try:
            subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60,
                }
            )
            print(f"✓ Created subscription: {subscription_path}", flush=True)
        except Exception as e:
            print(f"✗ Error creating subscription: {e}", flush=True)


def handle_underwriting_updated(message):
    """Handle underwriting.updated event (Workflow 1)."""
    try:
        data = json.loads(message.data.decode("utf-8"))
        underwriting_id = data.get("underwriting_id")

        print(f"\n{'='*70}", flush=True)
        print(f"📨 Received: underwriting.updated", flush=True)
        print(f"   Underwriting ID: {underwriting_id}", flush=True)
        print(f"{'='*70}", flush=True)

        # Create orchestrator and execute workflow
        conn = get_db_connection()
        orchestrator = create_orchestrator(conn)
        result = orchestrator.handle_workflow1(underwriting_id)
        conn.close()

        print(f"\n✅ Workflow 1 completed", flush=True)
        print(f"   Processors selected: {result.get('processors_selected', 0)}", flush=True)
        print(f"   Executions run: {result.get('executions_run', 0)}", flush=True)
        print(f"   Executions failed: {result.get('executions_failed', 0)}", flush=True)
        print(f"   Processors consolidated: {result.get('processors_consolidated', 0)}", flush=True)

        message.ack()
    except Exception as e:
        print(f"\n❌ Error processing underwriting.updated: {e}", flush=True)
        import traceback
        traceback.print_exc()

        # Determine if error is transient or permanent
        error_str = str(e).lower()
        transient_errors = [
            "connection",
            "timeout",
            "network",
            "temporarily unavailable",
            "resource temporarily unavailable",
        ]

        is_transient = any(err in error_str for err in transient_errors)

        if is_transient:
            print("   ⚠️  Transient error - will retry (NACK)", flush=True)
            message.nack()
        else:
            print("   ⚠️  Permanent error - skipping message (ACK)", flush=True)
            message.ack()


def handle_document_analyzed(message):
    """Handle document.analyzed event (Workflow 1)."""
    try:
        data = json.loads(message.data.decode("utf-8"))
        underwriting_id = data.get("underwriting_id")

        print(f"\n{'='*70}", flush=True)
        print(f"📨 Received: document.analyzed", flush=True)
        print(f"   Underwriting ID: {underwriting_id}", flush=True)
        print(f"{'='*70}", flush=True)

        # Create orchestrator and execute workflow
        conn = get_db_connection()
        orchestrator = create_orchestrator(conn)
        result = orchestrator.handle_workflow1(underwriting_id)
        conn.close()

        print(f"\n✅ Workflow 1 completed", flush=True)

        message.ack()
    except Exception as e:
        print(f"\n❌ Error processing document.analyzed: {e}", flush=True)
        import traceback
        traceback.print_exc()

        # Determine if error is transient or permanent
        error_str = str(e).lower()
        transient_errors = [
            "connection",
            "timeout",
            "network",
            "temporarily unavailable",
            "resource temporarily unavailable",
        ]

        is_transient = any(err in error_str for err in transient_errors)

        if is_transient:
            print("   ⚠️  Transient error - will retry (NACK)", flush=True)
            message.nack()
        else:
            print("   ⚠️  Permanent error - skipping message (ACK)", flush=True)
            message.ack()


def handle_underwriting_processor_execute(message):
    """Handle underwriting.processor.execute event (Workflow 2)."""
    try:
        data = json.loads(message.data.decode("utf-8"))

        print(f"\n{'='*70}", flush=True)
        print(f"📨 Received: underwriting.processor.execute", flush=True)
        print(f"   Payload: {data}", flush=True)
        print(f"{'='*70}", flush=True)

        # Extract parameters
        underwriting_processor_id = data.get("underwriting_processor_id")
        execution_id = data.get("execution_id")  # Optional - Scenario 1
        duplicate = data.get("duplicate", False)  # Optional - force duplicate
        application_form = data.get("application_form")  # Optional - Scenario 3
        document_list = data.get("document_list")  # Optional - Scenario 3

        # Validate required parameter
        if not underwriting_processor_id:
            print("   ❌ Missing required parameter: underwriting_processor_id", flush=True)
            message.ack()
            return

        # Create orchestrator and execute workflow
        conn = get_db_connection()
        orchestrator = create_orchestrator(conn)
        result = orchestrator.handle_workflow2(
            underwriting_processor_id=underwriting_processor_id,
            execution_id=execution_id,
            duplicate=duplicate,
            application_form=application_form,
            document_list=document_list,
        )
        conn.close()

        print(f"\n✅ Workflow 2 completed", flush=True)
        print(f"   Scenario: {result.get('scenario', 'unknown')}", flush=True)
        print(f"   Success: {result.get('success', False)}", flush=True)

        message.ack()
    except Exception as e:
        print(f"\n❌ Error processing underwriting.processor.execute: {e}", flush=True)
        import traceback
        traceback.print_exc()

        # Determine if error is transient or permanent
        error_str = str(e).lower()
        transient_errors = [
            "connection",
            "timeout",
            "network",
            "temporarily unavailable",
            "resource temporarily unavailable",
        ]

        is_transient = any(err in error_str for err in transient_errors)

        if is_transient:
            print("   ⚠️  Transient error - will retry (NACK)", flush=True)
            message.nack()
        else:
            print("   ⚠️  Permanent error - skipping message (ACK)", flush=True)
            message.ack()


def handle_underwriting_processor_consolidation(message):
    """Handle underwriting.processor.consolidation event (Workflow 3)."""
    try:
        data = json.loads(message.data.decode("utf-8"))
        underwriting_processor_id = data.get("underwriting_processor_id")

        print(f"\n{'='*70}", flush=True)
        print(f"📨 Received: underwriting.processor.consolidation", flush=True)
        print(f"   Underwriting Processor ID: {underwriting_processor_id}", flush=True)
        print(f"{'='*70}", flush=True)

        # Create orchestrator and execute workflow 3 (consolidation only)
        conn = get_db_connection()
        orchestrator = create_orchestrator(conn)
        result = orchestrator.handle_workflow3(underwriting_processor_id)
        conn.close()

        print(f"\n✅ Workflow 3 completed", flush=True)
        print(f"   Success: {result.get('success', False)}", flush=True)

        message.ack()
    except Exception as e:
        print(f"\n❌ Error processing underwriting.processor.consolidation: {e}", flush=True)
        import traceback
        traceback.print_exc()

        # Determine if error is transient or permanent
        error_str = str(e).lower()
        transient_errors = [
            "connection",
            "timeout",
            "network",
            "temporarily unavailable",
            "resource temporarily unavailable",
        ]

        is_transient = any(err in error_str for err in transient_errors)

        if is_transient:
            print("   ⚠️  Transient error - will retry (NACK)", flush=True)
            message.nack()
        else:
            print("   ⚠️  Permanent error - skipping message (ACK)", flush=True)
            message.ack()


def main():
    """Start Pub/Sub subscriber."""
    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║              AURA Pub/Sub Subscriber - Workflow Orchestrator         ║
    ╚══════════════════════════════════════════════════════════════════════╝

    Connecting to Pub/Sub emulator: localhost:8085
    Listening to topics:
      - underwriting.updated (Workflow 1)
      - document.analyzed (Workflow 1)
      - underwriting.processor.execute (Workflow 2)
      - underwriting.processor.consolidation (Workflow 3)

    Press Ctrl+C to stop...
    """, flush=True)

    # Create publisher and subscriber clients
    publisher = pubsub_v1.PublisherClient(credentials=AnonymousCredentials())
    subscriber = pubsub_v1.SubscriberClient(credentials=AnonymousCredentials())

    # Topic and subscription paths
    topics = {
        "underwriting.updated": handle_underwriting_updated,
        "document.analyzed": handle_document_analyzed,
        "underwriting.processor.execute": handle_underwriting_processor_execute,
        "underwriting.processor.consolidation": handle_underwriting_processor_consolidation,
    }

    # Create topics and subscriptions
    subscription_futures = []
    for topic_name, callback in topics.items():
        topic_path = f"projects/{PUBSUB_PROJECT}/topics/{topic_name}"
        subscription_path = f"projects/{PUBSUB_PROJECT}/subscriptions/{topic_name}-orchestrator-sub"

        print(f"\nSetting up topic: {topic_name}", flush=True)

        # Create topic if not exists
        create_topic_if_not_exists(publisher, topic_path)

        # Create subscription if not exists
        create_subscription_if_not_exists(subscriber, topic_path, subscription_path)

        # Subscribe with callback wrapper
        print(f"Subscribing to: {subscription_path}", flush=True)
        future = subscriber.subscribe(subscription_path, callback=callback)
        subscription_futures.append(future)
        print(f"✓ Listening: {topic_name}", flush=True)

    print("\n🎧 Subscriber is running...\n", flush=True)

    # Keep subscriber running
    running = True
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping subscriber...", flush=True)
        running = False
        for future in subscription_futures:
            future.cancel()
        print("✓ Subscriber stopped", flush=True)


class SubscriberReloader(FileSystemEventHandler):
    """File system event handler that restarts subscriber on changes."""

    def __init__(self):
        self.process = None
        self.restart_flag = False
        self.start_subscriber()

    def start_subscriber(self):
        """Start the subscriber process."""
        if self.process:
            print("\n🔄 Restarting subscriber...", flush=True)
            self.process.terminate()
            self.process.wait()
        else:
            print("🚀 Starting subscriber...", flush=True)

        # Start subscriber process
        subscriber_path = Path(__file__).resolve()
        self.process = subprocess.Popen(
            [sys.executable, str(subscriber_path)],
            stdout=sys.stdout,
            stderr=sys.stderr,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parent / "src")},
        )
        print(f"✅ Subscriber started (PID: {self.process.pid})\n", flush=True)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Only reload for Python files in processing_engine
        if event.src_path.endswith(".py") and "processing_engine" in event.src_path:
            # Avoid subscriber_reloader.py reloading itself
            if "subscriber" in event.src_path:
                return

            # Avoid too frequent reloads
            if not self.restart_flag:
                self.restart_flag = True
                time.sleep(0.5)  # Debounce
                self.start_subscriber()
                self.restart_flag = False

    def stop(self):
        """Stop the subscriber process."""
        if self.process:
            self.process.terminate()
            self.process.wait()


def main_with_reload():
    """Start subscriber with auto-reload."""
    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║          AURA Pub/Sub Subscriber - Auto-Reload Mode                  ║
    ╚══════════════════════════════════════════════════════════════════════╝

    Watching for file changes in: src/aura/processing_engine/
    Press Ctrl+C to stop...

    """, flush=True)

    # Create event handler and observer
    event_handler = SubscriberReloader()
    observer = Observer()

    # Watch the processing_engine directory
    watch_path = Path(__file__).parent / "src" / "aura" / "processing_engine"
    observer.schedule(event_handler, str(watch_path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping subscriber and file watcher...", flush=True)
        event_handler.stop()
        observer.stop()
        observer.join()
        print("✓ Stopped", flush=True)


if __name__ == "__main__":
    # Check if reload mode is requested
    if "--reload" in sys.argv:
        main_with_reload()
    else:
        main()

