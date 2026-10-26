# SecScan AI core module
import pytest
from advance_secscan_ai import EnterpriseSecScanAI, EnterpriseWebDashboard

def test_enterprise_web_dashboard_initialization():
    app_instance = EnterpriseSecScanAI()
    dashboard = EnterpriseWebDashboard(app_instance)
    assert dashboard.secscan_ai == app_instance
    assert dashboard.app is not None
