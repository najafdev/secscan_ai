# HACKNOVA core module
import pytest
from advance_hacknova import EnterpriseHackNova, EnterpriseWebDashboard

def test_enterprise_web_dashboard_initialization():
    app_instance = EnterpriseHackNova()
    dashboard = EnterpriseWebDashboard(app_instance)
    assert dashboard.hacknova == app_instance
    assert dashboard.app is not None
