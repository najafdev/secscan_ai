# SecScan AI core module
"""advance_secscan_ai optional-import helper."""

import advance_secscan_ai

def test_safe_import_missing_module_returns_none():
    assert advance_secscan_ai.safe_import("this_module_definitely_does_not_exist_xyz") is None

def test_safe_import_existing_module():
    assert advance_secscan_ai.safe_import("json") is not None
