# HACKNOVA core module
"""Config and credential defaults for advance_hacknova."""

import os
import pytest

@pytest.mark.parametrize("module_name", ["advance_hacknova"])
def test_database_url_from_env_overrides_config(tmp_path, monkeypatch, module_name):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@db:5432/test")
    mod = __import__(module_name)
    cfg = mod.Config(config_file=str(tmp_path / "test.ini"))
    assert cfg.DATABASE_URL == "postgresql://user:secret@db:5432/test"
    assert "hacknova123" not in cfg.DATABASE_URL

@pytest.mark.parametrize("module_name", ["advance_hacknova"])
def test_default_config_has_no_hardcoded_password(tmp_path, monkeypatch, module_name):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    mod = __import__(module_name)
    cfg = mod.Config(config_file=str(tmp_path / "fresh.ini"))
    assert "hacknova123" not in (cfg.DATABASE_URL or "")
