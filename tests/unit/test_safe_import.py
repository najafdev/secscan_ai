# HACKNOVA core module
"""advance_hacknova optional-import helper."""

import advance_hacknova

def test_safe_import_missing_module_returns_none():
    assert advance_hacknova.safe_import("this_module_definitely_does_not_exist_xyz") is None

def test_safe_import_existing_module():
    assert advance_hacknova.safe_import("json") is not None
