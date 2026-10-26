# SecScan AI core module
"""
Performance and Scalability Module

This module provides performance optimization and scalability features for SecScan AI,
including caching, parallel processing, load balancing, and performance monitoring.
"""

from .cache_manager import CacheManager, RedisCache, MemoryCache, get_cache_manager
from .parallel_processor import ParallelProcessor, TaskQueue, get_parallel_processor
from .performance_monitor import (
    PerformanceMonitor,
    MetricsCollector,
    get_performance_monitor,
)
from .load_balancer import LoadBalancer, HealthChecker, get_load_balancer
from .optimization import (
    QueryOptimizer,
    ResourceOptimizer,
    get_query_optimizer,
    get_resource_optimizer,
)

__version__ = "1.0.0"

__all__ = [
    "CacheManager",
    "RedisCache",
    "MemoryCache",
    "get_cache_manager",
    "ParallelProcessor",
    "TaskQueue",
    "get_parallel_processor",
    "PerformanceMonitor",
    "MetricsCollector",
    "get_performance_monitor",
    "LoadBalancer",
    "HealthChecker",
    "get_load_balancer",
    "QueryOptimizer",
    "ResourceOptimizer",
    "get_query_optimizer",
    "get_resource_optimizer",
]
