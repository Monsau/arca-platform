"""API-level contract tests: healthz, unknown artifact_kind -> 422."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src import main


def test_healthz_is_plain_and_unauthenticated():
    with TestClient(main.app) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.text == '"ok"' or resp.text == "ok"


def test_unknown_artifact_kind_returns_422(authed_client):
    resp = authed_client.post(
        "/api/v1/validate",
        json={"artifact_kind": "openapi_spec", "content": "x"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["supported_artifact_kinds"] == [
        "ontology_ttl",
        "ooc_manifest",
        "workflow_yaml",
    ]
    assert "openapi_spec" in detail["message"]
