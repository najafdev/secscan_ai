#!/usr/bin/env python3
# SecScan AI core module
"""
Performance Load Balancer for SecScan AI Enterprise
Distributes workload across multiple workers/processes
"""

import logging
import random
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Lock, Thread
from concurrent.futures import ThreadPoolExecutor, Future
import queue
import psutil


@dataclass
class Worker:
    """Represents a worker in the load balancer"""

    worker_id: str
    active: bool = True
    load: int = 0  # Current number of tasks
    max_load: int = 10  # Maximum concurrent tasks
    response_time: float = 0.0
    last_task: Optional[datetime] = None


class HealthChecker:
    """Health checker for workers"""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self.checking = False
        self.check_thread: Optional[Thread] = None

    def start_health_checks(self, workers: List[Worker]) -> None:
        """Start health checking"""
        if self.checking:
            return

        self.checking = True
        self.workers = workers
        self.check_thread = Thread(target=self._health_check_loop, daemon=True)
        self.check_thread.start()
        self.logger.info("Health checking started")

    def stop_health_checks(self) -> None:
        """Stop health checking"""
        self.checking = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        self.logger.info("Health checking stopped")

    def _health_check_loop(self) -> None:
        """Health check loop"""
        while self.checking:
            try:
                self._perform_health_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"Health check error: {str(e)}")
                time.sleep(self.check_interval)

    def _perform_health_checks(self) -> None:
        """Perform health checks on workers"""
        for worker in self.workers:
            # Simple health check - mark inactive if overloaded for too long
            if worker.load >= worker.max_load:
                if worker.last_task:
                    time_diff = (datetime.now() - worker.last_task).total_seconds()
                    if time_diff > 60:  # 1 minute timeout
                        worker.active = False
                        self.logger.warning(
                            f"Worker {worker.worker_id} marked inactive due to timeout"
                        )
            else:
                worker.active = True


class LoadBalancer:
    """Load balancer for distributing tasks across workers"""

    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)
        self.workers: List[Worker] = []
        self.max_workers = max_workers
        self._lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.health_checker = HealthChecker()
        self._current_worker = 0

        # Create default workers
        for i in range(max_workers):
            worker = Worker(worker_id=f"worker_{i}", active=True, max_load=5)
            self.workers.append(worker)

        self.health_checker.start_health_checks(self.workers)

    def add_worker(self, worker: Worker) -> None:
        """Add a worker to the pool"""
        with self._lock:
            self.workers.append(worker)
            self.logger.info(f"Added worker: {worker.worker_id}")

    def remove_worker(self, worker_id: str) -> bool:
        """Remove a worker from the pool"""
        with self._lock:
            for i, worker in enumerate(self.workers):
                if worker.worker_id == worker_id:
                    removed = self.workers.pop(i)
                    self.logger.info(f"Removed worker: {removed.worker_id}")
                    return True
        return False

    def get_best_worker(self, algorithm: str = "least_loaded") -> Optional[Worker]:
        """Get the best worker based on algorithm"""
        active_workers = [w for w in self.workers if w.active and w.load < w.max_load]

        if not active_workers:
            return None

        if algorithm == "round_robin":
            return self._round_robin(active_workers)
        elif algorithm == "least_loaded":
            return min(active_workers, key=lambda w: w.load)
        elif algorithm == "fastest":
            return min(active_workers, key=lambda w: w.response_time)
        elif algorithm == "random":
            return random.choice(active_workers)
        else:
            return self._round_robin(active_workers)

    def _round_robin(self, workers: List[Worker]) -> Worker:
        """Round-robin worker selection"""
        with self._lock:
            self._current_worker = (self._current_worker + 1) % len(workers)
            return workers[self._current_worker]

    def submit_task(self, func: Callable, *args, **kwargs) -> Optional[Future]:
        """Submit a task to be executed by the best available worker"""
        worker = self.get_best_worker()

        if not worker:
            self.logger.warning("No available workers for task")
            return None

        # Update worker state
        with self._lock:
            worker.load += 1
            worker.last_task = datetime.now()

        # Submit task
        future = self.executor.submit(self._execute_task, worker, func, *args, **kwargs)
        return future

    def _execute_task(self, worker: Worker, func: Callable, *args, **kwargs) -> Any:
        """Execute a task and track performance"""
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # Update worker performance
            execution_time = time.time() - start_time
            worker.response_time = (worker.response_time * 0.7) + (
                execution_time * 0.3
            )  # Moving average

            return result

        except Exception as e:
            self.logger.error(
                f"Task execution failed on worker {worker.worker_id}: {str(e)}"
            )
            raise

        finally:
            # Update worker state
            with self._lock:
                worker.load = max(0, worker.load - 1)

    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status"""
        with self._lock:
            active_count = sum(1 for w in self.workers if w.active)
            total_load = sum(w.load for w in self.workers)
            avg_response_time = (
                sum(w.response_time for w in self.workers) / len(self.workers)
                if self.workers
                else 0
            )

            return {
                "total_workers": len(self.workers),
                "active_workers": active_count,
                "inactive_workers": len(self.workers) - active_count,
                "total_load": total_load,
                "average_response_time": avg_response_time,
                "system_cpu_percent": psutil.cpu_percent(),
                "system_memory_percent": psutil.virtual_memory().percent,
                "workers": [
                    {
                        "worker_id": w.worker_id,
                        "active": w.active,
                        "load": w.load,
                        "max_load": w.max_load,
                        "response_time": w.response_time,
                        "utilization": (
                            (w.load / w.max_load) * 100 if w.max_load > 0 else 0
                        ),
                    }
                    for w in self.workers
                ],
            }

    def shutdown(self) -> None:
        """Shutdown the load balancer"""
        self.health_checker.stop_health_checks()
        self.executor.shutdown(wait=True)
        self.logger.info("Load balancer shutdown complete")


# Global load balancer instance
_load_balancer = None


def get_load_balancer() -> LoadBalancer:
    """Get singleton load balancer instance"""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer()
    return _load_balancer
