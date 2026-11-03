# HACKNOVA core module
"""Smoke imports for the advance_hacknova entry point."""


def test_advance_hacknova_core_classes_import():
    from advance_hacknova import EnterpriseHackNova, EnterpriseToolManager

    assert EnterpriseHackNova is not None
    assert EnterpriseToolManager is not None


def test_advance_hacknova_compatibility_aliases():
    from advance_hacknova import EnterpriseHackNova, HackNova, HackNova

    assert EnterpriseHackNova is not None
    assert HackNova is not None
    assert HackNova is not None
