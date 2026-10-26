#!/usr/bin/env python3
# SecScan AI core module
"""
Optimization Module for SecScan AI Enterprise
Query optimization and resource optimization utilities
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import psutil


@dataclass
class OptimizationRule:
    """Represents an optimization rule"""

    name: str
    condition: str
    action: str
    priority: int = 1
    enabled: bool = True


class QueryOptimizer:
    """Optimizes database and search queries"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.query_cache: Dict[str, Any] = {}
        self.optimization_rules: List[OptimizationRule] = []

    def add_rule(self, rule: OptimizationRule) -> None:
        """Add an optimization rule"""
        self.optimization_rules.append(rule)
        self.logger.info(f"Added optimization rule: {rule.name}")

    def optimize_query(self, query: str, query_type: str = "sql") -> str:
        """Optimize a query based on rules and patterns"""
        optimized_query = query.strip()

        # Apply optimization rules
        for rule in sorted(
            self.optimization_rules, key=lambda r: r.priority, reverse=True
        ):
            if not rule.enabled:
                continue

            if query_type in rule.condition or "all" in rule.condition:
                optimized_query = self._apply_rule(optimized_query, rule)

        return optimized_query

    def _apply_rule(self, query: str, rule: OptimizationRule) -> str:
        """Apply a specific optimization rule"""
        # Simple rule application - can be extended
        if "add_limit" in rule.action and "LIMIT" not in query.upper():
            if "SELECT" in query.upper():
                query += " LIMIT 1000"  # Add default limit

        if "add_index_hint" in rule.action:
            # Add index hints for common patterns
            pass

        return query

    def analyze_query_performance(
        self, query: str, execution_time: float
    ) -> Dict[str, Any]:
        """Analyze query performance and suggest optimizations"""
        analysis = {
            "query": query,
            "execution_time": execution_time,
            "performance_rating": "good",
            "suggestions": [],
        }

        # Performance thresholds
        if execution_time > 10.0:
            analysis["performance_rating"] = "poor"
            analysis["suggestions"].extend(
                [
                    "Consider adding database indexes",
                    "Review query complexity",
                    "Add result limiting",
                ]
            )
        elif execution_time > 2.0:
            analysis["performance_rating"] = "fair"
            analysis["suggestions"].append("Consider query optimization")

        # Query pattern analysis
        query_upper = query.upper()

        if "SELECT *" in query_upper:
            analysis["suggestions"].append("Avoid SELECT * - specify needed columns")

        if "ORDER BY" in query_upper and "LIMIT" not in query_upper:
            analysis["suggestions"].append("Add LIMIT clause to ordered queries")

        if query_upper.count("JOIN") > 3:
            analysis["suggestions"].append(
                "Complex joins detected - consider breaking into smaller queries"
            )

        return analysis


class ResourceOptimizer:
    """Optimizes system and application resource usage"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.optimization_history: List[Dict[str, Any]] = []

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Analyze and optimize memory usage"""
        memory = psutil.virtual_memory()

        optimization = {
            "timestamp": datetime.now().isoformat(),
            "memory_before": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
            },
            "optimizations_applied": [],
            "memory_after": None,
        }

        # Clear caches if memory usage is high
        if memory.percent > 85:
            self._clear_application_caches()
            optimization["optimizations_applied"].append("cleared_application_caches")

        # Force garbage collection
        if memory.percent > 80:
            import gc

            gc.collect()
            optimization["optimizations_applied"].append("forced_garbage_collection")

        # Get memory stats after optimization
        memory_after = psutil.virtual_memory()
        optimization["memory_after"] = {
            "total": memory_after.total,
            "available": memory_after.available,
            "percent": memory_after.percent,
            "used": memory_after.used,
        }

        self.optimization_history.append(optimization)
        return optimization

    def optimize_cpu_usage(self) -> Dict[str, Any]:
        """Analyze and optimize CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)

        optimization = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage_before": cpu_percent,
            "optimizations_applied": [],
            "cpu_usage_after": None,
        }

        # Reduce thread pool size if CPU usage is high
        if cpu_percent > 90:
            optimization["optimizations_applied"].append("cpu_throttling_recommended")

        # Get CPU usage after
        optimization["cpu_usage_after"] = psutil.cpu_percent(interval=1)

        self.optimization_history.append(optimization)
        return optimization

    def optimize_disk_usage(self) -> Dict[str, Any]:
        """Analyze and optimize disk usage"""
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100

        optimization = {
            "timestamp": datetime.now().isoformat(),
            "disk_usage_before": disk_percent,
            "optimizations_applied": [],
            "disk_usage_after": None,
        }

        # Clean up logs if disk usage is high
        if disk_percent > 90:
            self._cleanup_logs()
            optimization["optimizations_applied"].append("cleaned_old_logs")

        # Clean up temporary files
        if disk_percent > 85:
            self._cleanup_temp_files()
            optimization["optimizations_applied"].append("cleaned_temp_files")

        # Get disk usage after
        disk_after = psutil.disk_usage("/")
        disk_percent_after = (disk_after.used / disk_after.total) * 100
        optimization["disk_usage_after"] = disk_percent_after

        self.optimization_history.append(optimization)
        return optimization

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get system optimization recommendations"""
        recommendations = []

        # Memory recommendations
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            recommendations.append(
                {
                    "type": "memory",
                    "priority": "high",
                    "message": f"High memory usage: {memory.percent:.1f}%",
                    "actions": ["Clear caches", "Restart services", "Add more RAM"],
                }
            )

        # CPU recommendations
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            recommendations.append(
                {
                    "type": "cpu",
                    "priority": "high",
                    "message": f"High CPU usage: {cpu_percent:.1f}%",
                    "actions": [
                        "Reduce concurrent tasks",
                        "Optimize algorithms",
                        "Scale horizontally",
                    ],
                }
            )

        # Disk recommendations
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > 85:
            recommendations.append(
                {
                    "type": "disk",
                    "priority": "high",
                    "message": f"High disk usage: {disk_percent:.1f}%",
                    "actions": [
                        "Clean up logs",
                        "Archive old data",
                        "Add more storage",
                    ],
                }
            )

        return recommendations

    def _clear_application_caches(self) -> None:
        """Clear application caches"""
        # This would clear various application caches
        self.logger.info("Application caches cleared")

    def _cleanup_logs(self) -> None:
        """Clean up old log files"""
        # This would clean up old logs
        self.logger.info("Old logs cleaned up")

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files"""
        # This would clean up temporary files
        self.logger.info("Temporary files cleaned up")

    def get_optimization_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get optimization history"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)

        return [
            opt
            for opt in self.optimization_history
            if datetime.fromisoformat(opt["timestamp"]).timestamp() >= cutoff_time
        ]


# Global optimizer instances
_query_optimizer = None
_resource_optimizer = None


def get_query_optimizer() -> QueryOptimizer:
    """Get singleton query optimizer instance"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer()
    return _query_optimizer


def get_resource_optimizer() -> ResourceOptimizer:
    """Get singleton resource optimizer instance"""
    global _resource_optimizer
    if _resource_optimizer is None:
        _resource_optimizer = ResourceOptimizer()
    return _resource_optimizer
