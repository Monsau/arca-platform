from pathlib import Path

import pytest

from sdk.common.config import PlatformSettings, get_secret


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("ARCA_ENVIRONMENT", "testing")
    monkeypatch.setenv("ARCA_TENANT_ID", "tenant-42")
    settings = PlatformSettings()
    assert settings.environment == "testing"
    assert settings.tenant_id == "tenant-42"


def test_settings_load_from_json(tmp_path: Path):
    config = tmp_path / "config.json"
    config.write_text('{"environment": "staging", "log_level": "DEBUG"}')
    settings = PlatformSettings.load_from_file(config)
    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"


def test_get_secret_from_env(monkeypatch):
    monkeypatch.setenv("ARCA_SECRET_DB_PASSWORD", "hunter2")
    assert get_secret("DB_PASSWORD") == "hunter2"
