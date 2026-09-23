"""Workflow gates: schema, legacy-key normalization, malformed YAML."""
from __future__ import annotations

LEGACY_WORKFLOW = """
id: onboarding
steps:
  - id: enrich
    action: http_call
    sla_minutes: 30
    retry:
      max_attempts: 3
  - id: notify
    action: email
"""

CANONICAL_WORKFLOW = """
id: onboarding
steps:
  - id: enrich
    action: http_call
    sla_seconds: 1800
    retry:
      max_retries: 3
"""


def _validate(authed_client, content):
    resp = authed_client.post(
        "/api/v1/validate",
        json={"artifact_kind": "workflow_yaml", "content": content},
    )
    assert resp.status_code == 200
    return resp.json()


def test_legacy_keys_normalized_with_warnings(authed_client):
    body = _validate(authed_client, LEGACY_WORKFLOW)
    assert body["valid"] is True, body["detail"]
    normalized = body["normalized"]
    assert normalized is not None
    assert "sla_seconds" in normalized
    assert "max_retries" in normalized
    assert "sla_minutes" not in normalized
    assert "max_attempts" not in normalized
    warnings = [c for c in body["checks"] if c["severity"] == "warning"]
    assert len(warnings) == 2
    assert all(c["passed"] for c in warnings)
    assert any("sla_minutes" in c["message"] for c in warnings)
    assert any("max_attempts" in c["message"] for c in warnings)


def test_normalized_value_is_multiplied_by_60(authed_client):
    body = _validate(authed_client, LEGACY_WORKFLOW)
    import yaml

    doc = yaml.safe_load(body["normalized"])
    step = next(s for s in doc["steps"] if s["id"] == "enrich")
    assert step["sla_seconds"] == 1800
    assert step["retry"]["max_retries"] == 3


def test_canonical_workflow_normalized_is_null(authed_client):
    body = _validate(authed_client, CANONICAL_WORKFLOW)
    assert body["valid"] is True
    assert body["normalized"] is None
    assert not [c for c in body["checks"] if c["severity"] == "warning"]


def test_malformed_yaml_fails(authed_client):
    body = _validate(authed_client, "id: x\n  steps: [unclosed\n")
    assert body["valid"] is False
    schema = [c for c in body["checks"] if c["gate"] == "workflow-schema"]
    assert schema and all(not c["passed"] for c in schema)


def test_missing_steps_fails(authed_client):
    body = _validate(authed_client, "id: w\n")
    assert body["valid"] is False
    assert any("steps" in c["message"] for c in body["checks"] if not c["passed"])


def test_empty_steps_list_fails(authed_client):
    body = _validate(authed_client, "id: w\nsteps: []\n")
    assert body["valid"] is False
    assert any("steps" in c["message"] for c in body["checks"] if not c["passed"])


def test_missing_id_fails(authed_client):
    body = _validate(authed_client, "steps:\n  - id: s1\n")
    assert body["valid"] is False
    assert any("id" in c["message"] for c in body["checks"] if not c["passed"])
