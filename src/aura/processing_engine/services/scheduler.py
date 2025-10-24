"""
Underwriting Scheduler

Manages a queue-based scheduling system for underwriting processing.
Instead of skipping duplicate events, processes wait in a queue and execute in order.
"""

import threading
import queue
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import uuid


class UnderwritingScheduler:
    """
    Queue-based scheduler for underwriting processing.
    
    Instead of skipping duplicate events, this scheduler:
    1. Queues all events for the same underwriting_id
    2. Processes them sequentially in order
    3. Uses a worker thread pool to handle the queue
    4. Ensures only one workflow processes each underwriting at a time
    """
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self._queues: Dict[str, queue.Queue] = {}  # underwriting_id -> queue
        self._active_processors: Dict[str, str] = {}  # underwriting_id -> processor_id
        self._queue_locks: Dict[str, threading.Lock] = {}  # underwriting_id -> queue_lock
        self._manager_lock = threading.Lock()  # Protects the dictionaries
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="underwriting-scheduler")
        self._shutdown = False
        
        # Start the scheduler worker
        self._start_scheduler_worker()
    
    def _start_scheduler_worker(self):
        """Start the background worker that processes the queues."""
        def worker():
            while not self._shutdown:
                try:
                    # Check all queues for work
                    with self._manager_lock:
                        active_queues = list(self._queues.keys())
                    
                    for underwriting_id in active_queues:
                        if self._is_processing(underwriting_id):
                            continue  # Skip if already processing
                        
                        # Try to get work from this queue
                        work_item = self._get_next_work(underwriting_id)
                        if work_item:
                            # Submit to thread pool
                            future = self._executor.submit(self._process_work_item, work_item)
                    
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                except Exception as e:
                    print(f"    ❌ Scheduler worker error: {e}")
                    time.sleep(1)
        
        worker_thread = threading.Thread(target=worker, daemon=True, name="scheduler-worker")
        worker_thread.start()
    
    def schedule_workflow(self, underwriting_id: str, workflow_func: Callable, *args, **kwargs) -> str:
        """
        Schedule a workflow for processing.
        
        Args:
            underwriting_id: The underwriting ID to process
            workflow_func: The workflow function to execute
            *args: Arguments to pass to the workflow function
            **kwargs: Keyword arguments to pass to the workflow function
            
        Returns:
            str: Unique work item ID for tracking
        """
        work_item_id = str(uuid.uuid4())
        
        work_item = {
            "id": work_item_id,
            "underwriting_id": underwriting_id,
            "workflow_func": workflow_func,
            "args": args,
            "kwargs": kwargs,
            "created_at": datetime.now(),
            "status": "queued"
        }
        
        # Get or create queue for this underwriting_id
        with self._manager_lock:
            if underwriting_id not in self._queues:
                self._queues[underwriting_id] = queue.Queue()
                self._queue_locks[underwriting_id] = threading.Lock()
        
        # Add work to queue
        queue_lock = self._queue_locks[underwriting_id]
        with queue_lock:
            self._queues[underwriting_id].put(work_item)
        
        print(f"    📋 Queued work item {work_item_id} for underwriting {underwriting_id}")
        return work_item_id
    
    def _get_next_work(self, underwriting_id: str) -> Optional[Dict[str, Any]]:
        """Get the next work item from the queue for the given underwriting_id."""
        if underwriting_id not in self._queues:
            return None
        
        queue_lock = self._queue_locks[underwriting_id]
        with queue_lock:
            try:
                work_item = self._queues[underwriting_id].get_nowait()
                return work_item
            except queue.Empty:
                return None
    
    def _is_processing(self, underwriting_id: str) -> bool:
        """Check if the underwriting_id is currently being processed."""
        with self._manager_lock:
            return underwriting_id in self._active_processors
    
    def _process_work_item(self, work_item: Dict[str, Any]):
        """Process a work item (runs in thread pool)."""
        underwriting_id = work_item["underwriting_id"]
        work_item_id = work_item["id"]
        workflow_func = work_item["workflow_func"]
        args = work_item["args"]
        kwargs = work_item["kwargs"]
        
        # Mark as processing
        with self._manager_lock:
            self._active_processors[underwriting_id] = work_item_id
        
        print(f"    🚀 Processing work item {work_item_id} for underwriting {underwriting_id}")
        
        try:
            # Execute the workflow
            result = workflow_func(*args, **kwargs)
            work_item["status"] = "completed"
            work_item["result"] = result
            print(f"    ✅ Completed work item {work_item_id} for underwriting {underwriting_id}")
            
        except Exception as e:
            work_item["status"] = "failed"
            work_item["error"] = str(e)
            print(f"    ❌ Failed work item {work_item_id} for underwriting {underwriting_id}: {e}")
            
        finally:
            # Remove from active processors
            with self._manager_lock:
                if underwriting_id in self._active_processors:
                    del self._active_processors[underwriting_id]
    
    def get_queue_status(self, underwriting_id: str) -> Dict[str, Any]:
        """Get the status of the queue for a specific underwriting_id."""
        with self._manager_lock:
            if underwriting_id not in self._queues:
                return {"underwriting_id": underwriting_id, "queue_size": 0, "is_processing": False}
            
            queue_lock = self._queue_locks[underwriting_id]
            with queue_lock:
                queue_size = self._queues[underwriting_id].qsize()
            
            is_processing = underwriting_id in self._active_processors
            active_processor = self._active_processors.get(underwriting_id)
            
            return {
                "underwriting_id": underwriting_id,
                "queue_size": queue_size,
                "is_processing": is_processing,
                "active_processor": active_processor
            }
    
    def get_all_queues_status(self) -> Dict[str, Dict[str, Any]]:
        """Get the status of all queues."""
        with self._manager_lock:
            result = {}
            for underwriting_id in self._queues:
                result[underwriting_id] = self.get_queue_status(underwriting_id)
            return result
    
    def clear_queue(self, underwriting_id: str) -> int:
        """Clear all queued work for a specific underwriting_id."""
        with self._manager_lock:
            if underwriting_id not in self._queues:
                return 0
            
            queue_lock = self._queue_locks[underwriting_id]
            with queue_lock:
                cleared_count = 0
                try:
                    while True:
                        self._queues[underwriting_id].get_nowait()
                        cleared_count += 1
                except queue.Empty:
                    pass
            
            print(f"    🧹 Cleared {cleared_count} items from queue for underwriting {underwriting_id}")
            return cleared_count
    
    def shutdown(self):
        """Shutdown the scheduler and wait for all work to complete."""
        print("    🛑 Shutting down scheduler...")
        self._shutdown = True
        self._executor.shutdown(wait=True)
        print("    ✅ Scheduler shutdown complete")
    
    def __del__(self):
        """Cleanup on destruction."""
        if not self._shutdown:
            self.shutdown()


# Global scheduler instance
scheduler = UnderwritingScheduler(max_workers=3)
