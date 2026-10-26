#!/usr/bin/env python3
# SecScan AI core module
"""
Performance Monitor for SecScan AI Enterprise
Monitors system and application performance metrics
"""

import psutil
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Thread, Lock
import json


@dataclass
class PerformanceMetric:
    """Represents a performance metric"""

    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str = "general"


class PerformanceMonitor:
    """Monitors system and application performance"""

    def __init__(self, collection_interval: int = 5):
        self.logger = logging.getLogger(__name__)
        self.collection_interval = collection_interval
        self.metrics: List[PerformanceMetric] = []
        self.max_metrics = 1000  # Keep only last 1000 metrics
        self._lock = Lock()
        self.monitoring = False
        self.monitor_thread: Optional[Thread] = None

    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Performance monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {str(e)}")
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self) -> None:
        """Collect system performance metrics"""
        timestamp = datetime.now()

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        self._add_metric("cpu_usage_percent", cpu_percent, "%", timestamp, "system")

        # Memory metrics
        memory = psutil.virtual_memory()
        self._add_metric(
            "memory_usage_percent", memory.percent, "%", timestamp, "system"
        )
        self._add_metric(
            "memory_available_mb",
            memory.available / 1024 / 1024,
            "MB",
            timestamp,
            "system",
        )
        self._add_metric(
            "memory_used_mb", memory.used / 1024 / 1024, "MB", timestamp, "system"
        )

        # Disk metrics
        disk = psutil.disk_usage("/")
        disk_percent = (disk.used / disk.total) * 100
        self._add_metric("disk_usage_percent", disk_percent, "%", timestamp, "system")
        self._add_metric(
            "disk_free_gb", disk.free / 1024 / 1024 / 1024, "GB", timestamp, "system"
        )

        # Network metrics
        try:
            net_io = psutil.net_io_counters()
            self._add_metric(
                "network_bytes_sent", net_io.bytes_sent, "bytes", timestamp, "network"
            )
            self._add_metric(
                "network_bytes_recv", net_io.bytes_recv, "bytes", timestamp, "network"
            )
        except Exception:
            pass  # Network metrics might not be available

        # Process metrics for current process
        try:
            process = psutil.Process()
            self._add_metric(
                "process_memory_mb",
                process.memory_info().rss / 1024 / 1024,
                "MB",
                timestamp,
                "process",
            )
            self._add_metric(
                "process_cpu_percent", process.cpu_percent(), "%", timestamp, "process"
            )
            self._add_metric(
                "process_num_threads",
                process.num_threads(),
                "count",
                timestamp,
                "process",
            )
        except Exception:
            pass  # Process metrics might not be available

    def _add_metric(
        self,
        name: str,
        value: float,
        unit: str,
        timestamp: datetime,
        category: str = "general",
    ) -> None:
        """Add a metric to the collection"""
        with self._lock:
            metric = PerformanceMetric(name, value, unit, timestamp, category)
            self.metrics.append(metric)

            # Keep only the most recent metrics
            if len(self.metrics) > self.max_metrics:
                self.metrics = self.metrics[-self.max_metrics :]

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            if not self.metrics:
                return {}

            # Get the most recent metrics
            latest_metrics = {}
            for metric in reversed(self.metrics):
                if metric.name not in latest_metrics:
                    latest_metrics[metric.name] = {
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": metric.timestamp.isoformat(),
                        "category": metric.category,
                    }

            return latest_metrics

    def get_metrics_history(
        self, metric_name: str, minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)

            history = []
            for metric in self.metrics:
                if metric.name == metric_name and metric.timestamp >= cutoff_time:
                    history.append(
                        {
                            "value": metric.value,
                            "timestamp": metric.timestamp.isoformat(),
                        }
                    )

            return sorted(history, key=lambda x: x["timestamp"])

    def get_system_summary(self) -> Dict[str, Any]:
        """Get system performance summary"""
        current = self.get_current_metrics()

        summary = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_usage": current.get("cpu_usage_percent", {}).get("value", 0),
                "memory_usage": current.get("memory_usage_percent", {}).get("value", 0),
                "disk_usage": current.get("disk_usage_percent", {}).get("value", 0),
                "memory_available_mb": current.get("memory_available_mb", {}).get(
                    "value", 0
                ),
            },
            "process": {
                "memory_mb": current.get("process_memory_mb", {}).get("value", 0),
                "cpu_percent": current.get("process_cpu_percent", {}).get("value", 0),
                "num_threads": current.get("process_num_threads", {}).get("value", 0),
            },
        }

        return summary

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts"""
        alerts = []
        current = self.get_current_metrics()

        # CPU alert
        cpu_usage = current.get("cpu_usage_percent", {}).get("value", 0)
        if cpu_usage > 90:
            alerts.append(
                {
                    "type": "critical",
                    "metric": "cpu_usage",
                    "value": cpu_usage,
                    "threshold": 90,
                    "message": f"High CPU usage: {cpu_usage:.1f}%",
                }
            )
        elif cpu_usage > 75:
            alerts.append(
                {
                    "type": "warning",
                    "metric": "cpu_usage",
                    "value": cpu_usage,
                    "threshold": 75,
                    "message": f"Elevated CPU usage: {cpu_usage:.1f}%",
                }
            )

        # Memory alert
        memory_usage = current.get("memory_usage_percent", {}).get("value", 0)
        if memory_usage > 90:
            alerts.append(
                {
                    "type": "critical",
                    "metric": "memory_usage",
                    "value": memory_usage,
                    "threshold": 90,
                    "message": f"High memory usage: {memory_usage:.1f}%",
                }
            )
        elif memory_usage > 80:
            alerts.append(
                {
                    "type": "warning",
                    "metric": "memory_usage",
                    "value": memory_usage,
                    "threshold": 80,
                    "message": f"Elevated memory usage: {memory_usage:.1f}%",
                }
            )

        # Disk alert
        disk_usage = current.get("disk_usage_percent", {}).get("value", 0)
        if disk_usage > 95:
            alerts.append(
                {
                    "type": "critical",
                    "metric": "disk_usage",
                    "value": disk_usage,
                    "threshold": 95,
                    "message": f"High disk usage: {disk_usage:.1f}%",
                }
            )
        elif disk_usage > 85:
            alerts.append(
                {
                    "type": "warning",
                    "metric": "disk_usage",
                    "value": disk_usage,
                    "threshold": 85,
                    "message": f"Elevated disk usage: {disk_usage:.1f}%",
                }
            )

        return alerts


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get singleton performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Alias for backwards compatibility
MetricsCollector = PerformanceMonitor
