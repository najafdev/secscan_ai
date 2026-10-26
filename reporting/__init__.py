# SecScan AI core module
from .dynamic_reports import DynamicReportGenerator, ReportTemplate, ChartGenerator
from .realtime_dashboard import RealTimeDashboard


def get_realtime_dashboard():
    """Initialize and return the real-time dashboard"""
    return RealTimeDashboard()


__all__ = [
    "DynamicReportGenerator",
    "ReportTemplate",
    "ChartGenerator",
    "RealTimeDashboard",
    "get_realtime_dashboard",
]
