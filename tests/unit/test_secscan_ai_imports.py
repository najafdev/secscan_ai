# SecScan AI core module
"""Smoke imports for the advance_secscan_ai entry point."""


def test_advance_secscan_ai_core_classes_import():
    from advance_secscan_ai import EnterpriseSecScanAI, EnterpriseToolManager

    assert EnterpriseSecScanAI is not None
    assert EnterpriseToolManager is not None


def test_advance_secscan_ai_compatibility_aliases():
    from advance_secscan_ai import EnterpriseSecScanAI, SecScanAI, SecScanAI

    assert EnterpriseSecScanAI is not None
    assert SecScanAI is not None
    assert SecScanAI is not None
