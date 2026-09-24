"""Unit tests for the reference configuration adapter."""
import pytest

from adapters.configuration.configuration_adapter import FileConfigurationAdapter


DOC = {
    "environment": "staging",
    "adapters": {"secrets": "vault", "messaging": "kafka"},
    "messaging": {"bootstrap_servers": "kafka:9092"},
}


def test_loads_yaml_file(tmp_path):
    yaml = pytest.importorskip("yaml")
    path = tmp_path / "platform.yaml"
    path.write_text(yaml.safe_dump(DOC), encoding="utf-8")
    adapter = FileConfigurationAdapter(path)
    assert adapter.load()["environment"] == "staging"
    assert adapter.get("adapters.secrets") == "vault"
    assert adapter.get("messaging.bootstrap_servers") == "kafka:9092"


def test_loads_json_file(tmp_path):
    import json

    path = tmp_path / "platform.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    adapter = FileConfigurationAdapter(path)
    assert adapter.get("environment") == "staging"


def test_missing_key_returns_default(tmp_path):
    import json

    path = tmp_path / "platform.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    adapter = FileConfigurationAdapter(path)
    assert adapter.get("adapters.unknown", "fallback") == "fallback"
    assert adapter.get("nope.deep.key") is None


def test_missing_file_raises(tmp_path):
    adapter = FileConfigurationAdapter(tmp_path / "missing.yaml")
    with pytest.raises(FileNotFoundError):
        adapter.load()


def test_non_object_document_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('["not", "an", "object"]', encoding="utf-8")
    with pytest.raises(ValueError):
        FileConfigurationAdapter(path).load()


def test_reload_picks_up_changes(tmp_path):
    import json

    path = tmp_path / "platform.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    adapter = FileConfigurationAdapter(path)
    assert adapter.get("environment") == "staging"
    path.write_text(json.dumps({"environment": "production"}), encoding="utf-8")
    assert adapter.reload()["environment"] == "production"
