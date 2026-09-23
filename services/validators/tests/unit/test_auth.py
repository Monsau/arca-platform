"""Auth tests: no token, garbage token, wrong signature, valid token, JWKS path."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from conftest import AUDIENCE, make_token
from src import main


def _post(client, token=None, body=None):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    return client.post(
        "/api/v1/validate",
        json=body or {"artifact_kind": "ontology_ttl", "content": "@prefix ex: <http://ex.org/> ."},
        headers=headers,
    )


def test_no_token_returns_401():
    with TestClient(main.app) as client:
        resp = _post(client)
    assert resp.status_code == 401


def test_garbage_token_returns_401():
    with TestClient(main.app) as client:
        resp = _post(client, token="not.a.jwt")
    assert resp.status_code == 401


def test_wrong_scheme_returns_401(rsa_key):
    with TestClient(main.app) as client:
        resp = client.post(
            "/api/v1/validate",
            json={"artifact_kind": "ontology_ttl", "content": ""},
            headers={"Authorization": f"Basic abc"},
        )
    assert resp.status_code == 401


def test_auth_runs_before_any_validation_work():
    """Even a 422-worthy body must get 401 when the token is missing."""
    with TestClient(main.app) as client:
        resp = client.post("/api/v1/validate", json={"artifact_kind": "nonsense", "content": "x"})
    assert resp.status_code == 401


def test_wrong_signature_token_rejected(monkeypatch, rsa_key, other_rsa_key, jwks):
    """Structurally valid JWT signed by a key NOT in the JWKS -> 401."""

    async def fake_get_jwks():
        return jwks

    monkeypatch.setattr(main.token_validator, "_get_jwks", fake_get_jwks)
    bad_token = make_token(other_rsa_key)
    with TestClient(main.app) as client:
        resp = _post(client, token=bad_token)
    assert resp.status_code == 401


def test_expired_token_rejected(monkeypatch, rsa_key, jwks):
    async def fake_get_jwks():
        return jwks

    monkeypatch.setattr(main.token_validator, "_get_jwks", fake_get_jwks)
    now = int(time.time())
    expired = make_token(rsa_key, iat=now - 3600, exp=now - 600)
    with TestClient(main.app) as client:
        resp = _post(client, token=expired)
    assert resp.status_code == 401


def test_wrong_audience_rejected(monkeypatch, rsa_key, jwks):
    async def fake_get_jwks():
        return jwks

    monkeypatch.setattr(main.token_validator, "_get_jwks", fake_get_jwks)
    token = make_token(rsa_key, aud="some-other-service")
    with TestClient(main.app) as client:
        resp = _post(client, token=token)
    assert resp.status_code == 401


def test_audience_as_list_accepted(monkeypatch, rsa_key, jwks):
    """aud as a list containing the configured audience must be accepted."""
    monkeypatch.setattr(
        main.token_validator, "_get_jwks", _static_jwks(jwks)
    )
    token = make_token(rsa_key, aud=["account", AUDIENCE])
    with TestClient(main.app) as client:
        resp = _post(client, token=token)
    assert resp.status_code == 200
    assert resp.json()["artifact_kind"] == "ontology_ttl"


def test_valid_token_accepted(monkeypatch, rsa_key, jwks):
    monkeypatch.setattr(main.token_validator, "_get_jwks", _static_jwks(jwks))
    token = make_token(rsa_key)
    with TestClient(main.app) as client:
        resp = _post(client, token=token)
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True  # minimal but parseable turtle, empty data graph
    assert body["normalized"] is None
    assert isinstance(body["checks"], list) and body["checks"]
    assert isinstance(body["detail"], str) and body["detail"]


def _static_jwks(jwks):
    async def fake_get_jwks():
        return jwks

    return fake_get_jwks


def test_auth_dependency_spy(authed_client, monkeypatch):
    """Non-auth tests go through a stubbed dependency; make sure it is the one
    being used and that a monkeypatched validator is not accidentally called."""
    called = []

    async def spy_validate(token):
        called.append(token)
        return {"sub": "spy"}

    monkeypatch.setattr(main.token_validator, "validate", spy_validate)
    resp = authed_client.post(
        "/api/v1/validate",
        json={"artifact_kind": "workflow_yaml", "content": "id: w\nsteps:\n  - id: s1\n"},
    )
    assert resp.status_code == 200
    assert called == []  # dependency override short-circuits the validator
