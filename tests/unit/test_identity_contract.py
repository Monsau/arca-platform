"""Tests for the identity contract and JWT adapter."""

import json
from pathlib import Path

import jwt
import pytest

from adapters.identity.jwt_adapter import (
    IdentityToken,
    JWTIdentityAdapter,
    ServiceAccount,
    WorkloadIdentity,
)

SCHEMAS_DIR = Path(__file__).parents[2] / "schemas" / "identity"


def _load_schema(name: str) -> dict:
    with open(SCHEMAS_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def test_identity_token_dataclass():
    token = IdentityToken(
        subject="user-1",
        issuer="https://idp.arca.local",
        audience=["arca-decision-room"],
        scopes=["read", "write"],
        claims={"sub": "user-1"},
    )
    assert token.subject == "user-1"
    assert token.scopes == ["read", "write"]


def test_workload_identity_defaults():
    wi = WorkloadIdentity(workload_id="spiffe://cluster/ns/default/sa/app", issuer="https://idp.arca.local")
    assert wi.service_account == ""
    assert wi.attributes == {}


def test_service_account_defaults():
    sa = ServiceAccount(account_id="sa-1", account_name="app-service", issuer="https://idp.arca.local")
    assert sa.scopes == []


def test_jwt_adapter_validates_token():
    payload = {
        "sub": "user-1",
        "iss": "https://idp.arca.local",
        "aud": "arca-platform",
        "exp": 9999999999,
        "iat": 1700000000,
        "scope": "read write",
    }
    token = jwt.encode(payload, "secret", algorithm="HS256")
    adapter = JWTIdentityAdapter(issuer="https://idp.arca.local")
    identity = adapter.validate(token)
    assert identity.subject == "user-1"
    assert identity.issuer == "https://idp.arca.local"
    assert identity.audience == "arca-platform"
    assert identity.scopes == ["read", "write"]


def test_jwt_adapter_workload_identity():
    payload = {
        "sub": "sa-1",
        "iss": "https://idp.arca.local",
        "aud": "arca-platform",
        "exp": 9999999999,
        "iat": 1700000000,
        "client_id": "app-service",
        "roles": ["service"],
    }
    token = jwt.encode(payload, "secret", algorithm="HS256")
    adapter = JWTIdentityAdapter(issuer="https://idp.arca.local")
    workload = adapter.workload_identity(token)
    assert workload.workload_id == "sa-1"
    assert workload.service_account == "app-service"
    assert workload.attributes["roles"] == ["service"]


def test_openid_configuration_schema_has_required_fields():
    schema = _load_schema("openid-configuration-schema.json")
    required = schema.get("required", [])
    assert "issuer" in required
    assert "jwks_uri" in required


def test_jwt_claims_schema_has_required_claims():
    schema = _load_schema("jwt-claims-schema.json")
    required = schema.get("required", [])
    assert set(required) >= {"sub", "iss", "aud", "exp", "iat"}


def test_workload_identity_schema_has_required_fields():
    schema = _load_schema("workload-identity-schema.json")
    required = schema.get("required", [])
    assert "workload_id" in required
    assert "issuer" in required
