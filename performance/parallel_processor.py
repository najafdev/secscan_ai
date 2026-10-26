#!/usr/bin/env python3
# SecScan AI core module
"""
Parallel Processing Engine for SecScan AI
Handles parallel execution, task queuing, and distributed processing
"""

import os
import time
import threading
import multiprocessing
import logging
import queue
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

def _utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed
from enum import Enum
import uuid
import json

try:
    import celery
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available. Install with: pip install celery")

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    logging.warning("aioredis not available. Install with: pip install aioredis")

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    CANCELLED = "cancelled"

@dataclass
class Task:
    task_id: str
    function_name: str
    args: tuple
    kwargs: dict
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0
    timeout: Optional[int] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    worker_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = _utc_now()

@dataclass
class WorkerStats:
    worker_id: str
    started_at: datetime
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    status: str = "idle"  # idle, busy, stopped

class TaskQueue:
    """Priority task queue with persistence"""
    
    def __init__(self, maxsize: int = 0):
        self.queue = queue.PriorityQueue(maxsize=maxsize)
        self.tasks: Dict[str, Task] = {}
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
    def put(self, task: Task, block: bool = True, timeout: Optional[float] = None):
        """Add task to queue"""
        with self.lock:
            # Priority queue uses (priority, timestamp, task_id, item) tuples
            # Lower numbers = higher priority; task_id prevents unorderable Task comparison
            priority_item = (-task.priority, task.created_at.timestamp(), task.task_id, task)
            
            self.queue.put(priority_item, block=block, timeout=timeout)
            self.tasks[task.task_id] = task
            
        self.logger.debug(f"Added task {task.task_id} to queue")
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Task:
        """Get next task from queue"""
        try:
            priority_item = self.queue.get(block=block, timeout=timeout)
            task = priority_item[3]  # Extract task from priority tuple
            
            with self.lock:
                task.status = TaskStatus.RUNNING
                task.started_at = _utc_now()
                
            return task
            
        except queue.Empty:
            raise
    
    def task_done(self):
        """Mark task as done"""
        self.queue.task_done()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def update_task(self, task: Task):
        """Update task status"""
        with self.lock:
            self.tasks[task.task_id] = task
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        with self.lock:
            return [task for task in self.tasks.values() 
                   if task.status == TaskStatus.PENDING]
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        with self.lock:
            stats = {}
            for status in TaskStatus:
                stats[status.value] = sum(
                    1 for task in self.tasks.values() 
                    if task.status == status
                )
            stats["queue_size"] = self.queue.qsize()
            return stats

class Worker:
    """Worker process for executing tasks"""
    
    def __init__(self, worker_id: str, task_queue: TaskQueue, 
                 task_registry: Dict[str, Callable]):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.task_registry = task_registry
        self.stats = WorkerStats(
            worker_id=worker_id,
            started_at=_utc_now()
        )
        self.running = False
        self.logger = logging.getLogger(f"worker-{worker_id}")
    
    def start(self):
        """Start worker loop"""
        self.running = True
        self.stats.status = "idle"
        self.logger.info(f"Worker {self.worker_id} started")
        
        while self.running:
            try:
                # Get next task with timeout
                task = self.task_queue.get(timeout=5)
                self.process_task(task)
                self.task_queue.task_done()
                
            except queue.Empty:
                # No tasks available, update heartbeat
                self.stats.last_heartbeat = _utc_now()
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                time.sleep(1)
        
        self.stats.status = "stopped"
        self.logger.info(f"Worker {self.worker_id} stopped")
    
    def process_task(self, task: Task):
        """Process a single task"""
        self.stats.current_task = task.task_id
        self.stats.status = "busy"
        
        try:
            # Get task function
            if task.function_name not in self.task_registry:
                raise ValueError(f"Unknown task function: {task.function_name}")
            
            task_func = self.task_registry[task.function_name]
            
            # Execute task with timeout
            if task.timeout:
                result = self._execute_with_timeout(
                    task_func, task.args, task.kwargs, task.timeout
                )
            else:
                result = task_func(*task.args, **task.kwargs)
            
            # Update task status
            task.status = TaskStatus.SUCCESS
            task.result = result
            task.completed_at = _utc_now()
            task.worker_id = self.worker_id
            
            self.stats.tasks_completed += 1
            self.logger.debug(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Task {task.task_id} failed: {e}")
            
            task.error = str(e)
            task.retry_count += 1
            
            if task.retry_count <= task.max_retries:
                # Retry task
                task.status = TaskStatus.RETRY
                task.started_at = None
                self.task_queue.put(task)  # Re-queue for retry
                self.logger.info(f"Task {task.task_id} queued for retry ({task.retry_count}/{task.max_retries})")
            else:
                # Mark as failed
                task.status = TaskStatus.FAILURE
                task.completed_at = _utc_now()
                self.stats.tasks_failed += 1
        
        finally:
            # Update task in queue
            self.task_queue.update_task(task)
            self.stats.current_task = None
            self.stats.status = "idle"
            self.stats.last_heartbeat = _utc_now()
    
    def _execute_with_timeout(self, func: Callable, args: tuple, 
                             kwargs: dict, timeout: int) -> Any:
        """Execute function with timeout using threading"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # Thread is still running, timeout occurred
            raise TimeoutError(f"Task execution timeout after {timeout} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def stop(self):
        """Stop worker"""
        self.running = False

class ParallelProcessor:
    """Main parallel processing engine"""
    
    def __init__(self, 
                 max_workers: int = None,
                 max_processes: int = None,
                 queue_size: int = 1000,
                 use_celery: bool = False,
                 redis_url: str = "redis://localhost:6379/0"):
        
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.max_processes = max_processes or (os.cpu_count() or 1)
        self.task_queue = TaskQueue(maxsize=queue_size)
        self.task_registry: Dict[str, Callable] = {}
        self.workers: List[Worker] = []
        self.worker_threads: List[threading.Thread] = []
        self.thread_executor = None
        self.process_executor = None
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Celery integration
        self.use_celery = use_celery and CELERY_AVAILABLE
        self.celery_app = None
        
        if self.use_celery:
            self._setup_celery(redis_url)
    
    def _setup_celery(self, redis_url: str):
        """Setup Celery for distributed task processing"""
        self.celery_app = Celery(
            'secscan_ai-tasks',
            broker=redis_url,
            backend=redis_url
        )
        
        # Configure Celery
        self.celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,  # 30 minutes
            task_soft_time_limit=25 * 60,  # 25 minutes
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
        )
        
        self.logger.info("Celery configured for distributed processing")
    
    def register_task(self, name: str, func: Callable):
        """Register a task function"""
        self.task_registry[name] = func
        
        # Also register with Celery if available
        if self.celery_app:
            self.celery_app.task(name=name)(func)
        
        self.logger.debug(f"Registered task: {name}")
    
    def submit_task(self, function_name: str, *args, 
                   priority: int = 0, max_retries: int = 3,
                   timeout: Optional[int] = None, **kwargs) -> str:
        """Submit a task for execution"""
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            function_name=function_name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
            timeout=timeout
        )
        
        if self.use_celery:
            # Submit to Celery
            celery_task = self.celery_app.send_task(
                function_name,
                args=args,
                kwargs=kwargs,
                task_id=task_id
            )
            task.status = TaskStatus.PENDING
        else:
            # Submit to local queue
            self.task_queue.put(task)
        
        self.logger.info(f"Submitted task {task_id}: {function_name}")
        return task_id
    
    def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Get task result (blocking)"""
        if self.use_celery:
            # Get result from Celery
            result = self.celery_app.AsyncResult(task_id)
            return result.get(timeout=timeout)
        else:
            # Poll local task queue
            start_time = time.time()
            while True:
                task = self.task_queue.get_task(task_id)
                if not task:
                    raise ValueError(f"Task {task_id} not found")
                
                if task.status == TaskStatus.SUCCESS:
                    return task.result
                elif task.status == TaskStatus.FAILURE:
                    raise Exception(f"Task failed: {task.error}")
                elif task.status == TaskStatus.CANCELLED:
                    raise RuntimeError(f"Task {task_id} was cancelled")
                
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Task result timeout after {timeout} seconds")
                
                time.sleep(0.1)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        if self.use_celery:
            result = self.celery_app.AsyncResult(task_id)
            return {
                "task_id": task_id,
                "status": result.status.lower(),
                "result": result.result if result.successful() else None,
                "error": str(result.result) if result.failed() else None
            }
        else:
            task = self.task_queue.get_task(task_id)
            if task:
                return asdict(task)
            return None
    
    def start(self):
        """Start the parallel processor"""
        if self.running:
            return
        
        self.running = True
        
        # Start thread pool executor
        self.thread_executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="secscan_ai-thread"
        )
        
        # Start process pool executor
        self.process_executor = ProcessPoolExecutor(
            max_workers=self.max_processes
        )
        
        if not self.use_celery:
            # Start local workers
            for i in range(min(4, self.max_workers)):  # Start 4 dedicated workers
                worker_id = f"worker-{i}"
                worker = Worker(worker_id, self.task_queue, self.task_registry)
                
                worker_thread = threading.Thread(
                    target=worker.start,
                    name=f"secscan_ai-{worker_id}"
                )
                worker_thread.daemon = True
                worker_thread.start()
                
                self.workers.append(worker)
                self.worker_threads.append(worker_thread)
        
        self.logger.info(f"Parallel processor started with {self.max_workers} thread workers and {self.max_processes} process workers")
    
    def stop(self):
        """Stop the parallel processor"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop workers
        for worker in self.workers:
            worker.stop()
        
        # Wait for worker threads
        for thread in self.worker_threads:
            thread.join(timeout=5)
        
        # Shutdown executors
        if self.thread_executor:
            self.thread_executor.shutdown(wait=True)
        
        if self.process_executor:
            self.process_executor.shutdown(wait=True)
        
        self.logger.info("Parallel processor stopped")
    
    def execute_parallel(self, func: Callable, items: List[Any], 
                        max_workers: int = None, use_processes: bool = False) -> List[Any]:
        """Execute function in parallel on list of items"""
        if not self.running:
            self.start()
        
        executor = self.process_executor if use_processes else self.thread_executor
        actual_max_workers = max_workers or (self.max_processes if use_processes else self.max_workers)
        
        # Split items into smaller chunks if needed
        chunk_size = max(1, len(items) // actual_max_workers)
        if not use_processes:
            chunk_size = 1  # No chunking for threads
        
        futures = []
        results = []
        
        try:
            if chunk_size == 1:
                # Submit individual items
                for item in items:
                    future = executor.submit(func, item)
                    futures.append(future)
            else:
                # Submit chunks
                for i in range(0, len(items), chunk_size):
                    chunk = items[i:i + chunk_size]
                    future = executor.submit(self._process_chunk, func, chunk)
                    futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if chunk_size == 1:
                        results.append(result)
                    else:
                        results.extend(result)
                except Exception as e:
                    self.logger.error(f"Task execution error: {e}")
                    results.append(None)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Parallel execution error: {e}")
            return []
    
    def _process_chunk(self, func: Callable, chunk: List[Any]) -> List[Any]:
        """Process a chunk of items"""
        return [func(item) for item in chunk]
    
    def execute_pipeline(self, pipeline: List[Dict[str, Any]], 
                        data: Any, parallel: bool = True) -> Any:
        """Execute a processing pipeline"""
        current_data = data
        
        for stage in pipeline:
            stage_name = stage.get('name', 'unknown')
            stage_func = stage.get('function')
            stage_args = stage.get('args', [])
            stage_kwargs = stage.get('kwargs', {})
            stage_parallel = stage.get('parallel', parallel)
            
            if not stage_func:
                continue
            
            try:
                if isinstance(current_data, list) and stage_parallel:
                    # Process list items in parallel
                    current_data = self.execute_parallel(
                        lambda item: stage_func(item, *stage_args, **stage_kwargs),
                        current_data
                    )
                else:
                    # Process sequentially
                    current_data = stage_func(current_data, *stage_args, **stage_kwargs)
                
                self.logger.debug(f"Completed pipeline stage: {stage_name}")
                
            except Exception as e:
                self.logger.error(f"Pipeline stage {stage_name} failed: {e}")
                raise
        
        return current_data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        stats = {
            "running": self.running,
            "max_workers": self.max_workers,
            "max_processes": self.max_processes,
            "registered_tasks": len(self.task_registry),
            "use_celery": self.use_celery,
            "queue_stats": self.task_queue.get_stats(),
            "workers": []
        }
        
        # Add worker stats
        for worker in self.workers:
            stats["workers"].append(asdict(worker.stats))
        
        return stats

# Global processor instance
_processor = None

def get_parallel_processor() -> ParallelProcessor:
    """Get global parallel processor instance"""
    global _processor
    
    if _processor is None:
        _processor = ParallelProcessor()
        _processor.start()
    
    return _processor

# Decorators for easy parallel execution
def parallel_task(name: str = None, priority: int = 0, 
                 max_retries: int = 3, timeout: int = None):
    """Decorator to register and submit parallel tasks"""
    def decorator(func):
        task_name = name or f"{func.__module__}.{func.__name__}"
        
        # Register task
        processor = get_parallel_processor()
        processor.register_task(task_name, func)
        
        def wrapper(*args, **kwargs):
            # Submit task for parallel execution
            task_id = processor.submit_task(
                task_name, *args,
                priority=priority,
                max_retries=max_retries,
                timeout=timeout,
                **kwargs
            )
            return task_id
        
        # Add sync execution method
        wrapper.sync = func
        wrapper.task_name = task_name
        
        return wrapper
    
    return decorator

def parallel_map(func: Callable, items: List[Any], 
                max_workers: int = None, use_processes: bool = False) -> List[Any]:
    """Parallel map function"""
    processor = get_parallel_processor()
    return processor.execute_parallel(func, items, max_workers, use_processes)
