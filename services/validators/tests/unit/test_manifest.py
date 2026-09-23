"""OOC manifest gate: schema rules, JSON/YAML parsing, real pack manifest."""
from __future__ import annotations

import json
from pathlib import Path

MOROCCO_MANIFEST = Path(
    r"C:\projets\innovation\arca-packs\src\packs\morocco-sovereignty\manifest.yaml"
)

VALID_MANIFEST = {
    "pack_id": "demo-pack",
    "version": "1.2.3",
    "metadata": {"owner": "team/arca", "support_model": "standard"},
    "artifacts": {"ontology": "ontology/"},
}


def _validate(authed_client, content, content_format=None):
    payload = {"artifact_kind": "ooc_manifest", "content": content}
    if content_format:
        payload["content_format"] = content_format
    resp = authed_client.post("/api/v1/validate", json=payload)
    assert resp.status_code == 200
    return resp.json()


def _schema_failures(body):
    return [
        c["message"]
        for c in body["checks"]
        if c["gate"] == "manifest-schema" and not c["passed"]
    ]


def test_valid_json_manifest(authed_client):
    body = _validate(authed_client, json.dumps(VALID_MANIFEST), content_format="json")
    assert body["valid"] is True, body["detail"]


def test_valid_manifest_without_explicit_format(authed_client):
    body = _validate(authed_client, json.dumps(VALID_MANIFEST))
    assert body["valid"] is True


def test_yaml_manifest_without_explicit_format(authed_client):
    import yaml

    body = _validate(authed_client, yaml.safe_dump(VALID_MANIFEST))
    assert body["valid"] is True


def test_missing_pack_id_fails(authed_client):
    doc = dict(VALID_MANIFEST, pack_id=None)
    body = _validate(authed_client, json.dumps(doc))
    assert body["valid"] is False
    assert any("pack_id" in m for m in _schema_failures(body))


def test_invalid_pack_id_regex(authed_client):
    body = _validate(authed_client, json.dumps(dict(VALID_MANIFEST, pack_id="Bad_Pack")))
    assert body["valid"] is False
    assert any("Bad_Pack" in m for m in _schema_failures(body))


def test_invalid_semver_fails(authed_client):
    body = _validate(authed_client, json.dumps(dict(VALID_MANIFEST, version="1.2")))
    assert body["valid"] is False
    assert any("semver" in m for m in _schema_failures(body))


def test_missing_owner_fails(authed_client):
    doc = dict(VALID_MANIFEST, metadata={"support_model": "premium"})
    body = _validate(authed_client, json.dumps(doc))
    assert body["valid"] is False
    assert any("owner" in m for m in _schema_failures(body))


def test_invalid_support_model_fails(authed_client):
    doc = dict(VALID_MANIFEST, metadata={"owner": "x", "support_model": "gold"})
    body = _validate(authed_client, json.dumps(doc))
    assert body["valid"] is False
    assert any("support_model" in m for m in _schema_failures(body))


def test_empty_artifacts_fail(authed_client):
    body = _validate(authed_client, json.dumps(dict(VALID_MANIFEST, artifacts={})))
    assert body["valid"] is False
    assert any("artifact" in m for m in _schema_failures(body))


def test_multiple_failures_each_reported(authed_client):
    doc = {"pack_id": "Bad Pack", "version": "v1", "metadata": {}, "artifacts": {}}
    body = _validate(authed_client, json.dumps(doc))
    assert body["valid"] is False
    failures = _schema_failures(body)
    assert len(failures) == 4  # pack_id, version, owner, artifacts
    assert any("pack_id" in m for m in failures)
    assert any("semver" in m for m in failures)
    assert any("owner" in m for m in failures)
    assert any("artifact" in m for m in failures)


def test_garbage_content_fails(authed_client):
    body = _validate(authed_client, "{ not json ]", content_format="json")
    assert body["valid"] is False
    assert any("JSON" in c["message"] for c in body["checks"] if not c["passed"])


def test_real_morocco_manifest_valid(authed_client):
    assert MOROCCO_MANIFEST.exists(), f"fixture missing: {MOROCCO_MANIFEST}"
    body = _validate(authed_client, MOROCCO_MANIFEST.read_text(encoding="utf-8"), "yaml")
    assert body["valid"] is True, body["detail"]
