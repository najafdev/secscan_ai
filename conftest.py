# SecScan AI core module
"""Pytest root config — stub heavy deps before secscan_ai.py is imported."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _stub(name: str) -> types.ModuleType:
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
    return sys.modules[name]


for _mod in (
    "openai",
    "speech_recognition",
    "pyttsx3",
    "pypandoc",
    "cvsslib",
    "flask",
    "flask_cors",
    "redis",
    "psycopg2",
    "sqlalchemy",
    "celery",
    "docker",
    "kubernetes",
    "consul",
    "jwt",
    "bcrypt",
    "ldap3",
    "numpy",
    "pandas",
    "seaborn",
    "websockets",
    "aiohttp",
    "requests",
):
    _stub(_mod)

for _name in ("Flask", "render_template", "request", "jsonify", "session"):
    setattr(_stub("flask"), _name, MagicMock())
_stub("flask_cors").CORS = MagicMock()
_stub("celery").Celery = MagicMock()
for _name in ("Server", "Connection", "ALL"):
    setattr(_stub("ldap3"), _name, MagicMock())

matplotlib = _stub("matplotlib")
matplotlib.use = MagicMock()
_stub("matplotlib.pyplot")
_stub("sklearn.cluster").DBSCAN = MagicMock()
_stub("sklearn.ensemble").IsolationForest = MagicMock()

_internal = {
    "database": [
        "get_db_manager",
        "PentestSession",
        "Vulnerability",
        "User",
        "AuditLog",
        "AIContext",
    ],
    "security": [
        "EnterpriseAuth", "ComplianceFrameworkMapper", "get_soc_analyzer",
        "AdvancedSOCAnalyzer", "ThreatSeverity", "LogFormat", "SOCAlert",
        "NormalizedLogEntry", "IOCResult", "AnomalyResult", "IncidentTimeline",
        "Playbook", "SOCAnalysisReport", "SIEMConnectorType", "SIEMConnector",
        "SplunkConnector", "QRadarConnector", "ElasticsearchConnector",
        "WebhookConnector", "SIEMConnectorManager"
    ],
    "exploitation": ["AdvancedExploitationEngine", "ZeroDayDetector"],
    "reporting": ["DynamicReportGenerator", "get_realtime_dashboard"],
    "cloud": ["DockerManager", "KubernetesManager", "ServiceRegistry"],
    "performance": ["get_cache_manager", "get_parallel_processor"],
}
for pkg, names in _internal.items():
    try:
        # Try importing the real package if it exists locally
        import importlib
        mod = importlib.import_module(pkg)
    except ImportError:
        mod = _stub(pkg)
    for sym in names:
        if not hasattr(mod, sym):
            setattr(mod, sym, MagicMock())


