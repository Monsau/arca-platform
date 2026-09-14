"""Tests for the policy contract and reference adapters."""

import json
from pathlib import Path

import pytest

from adapters.policy.policy_adapter import (
    Decision,
    NullPolicyAdapter,
    PolicyEvalRequest,
    PolicyEvalResponse,
    StaticPolicyAdapter,
)

SCHEMAS_DIR = Path(__file__).parents[2] / "schemas" / "policy"


def _load_schema(name: str) -> dict:
    with open(SCHEMAS_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def test_null_policy_adapter_default_deny():
    adapter = NullPolicyAdapter()
    request = PolicyEvalRequest(
        subject={"id": "user-1"},
        resource={"type": "decision", "id": "d-1"},
        action="seal",
    )
    response = adapter.evaluate(request)
    assert response.decision is Decision.DENY


def test_null_policy_adapter_permit_all():
    adapter = NullPolicyAdapter(default_decision=Decision.PERMIT)
    request = PolicyEvalRequest(
        subject={"id": "user-1"},
        resource={"type": "decision"},
        action="seal",
    )
    response = adapter.evaluate(request)
    assert response.decision is Decision.PERMIT


def test_static_policy_adapter_permits_matching_role():
    adapter = StaticPolicyAdapter(
        role_permissions={"sealer": [("decision", "seal")]}
    )
    request = PolicyEvalRequest(
        subject={"id": "user-1", "roles": ["sealer"]},
        resource={"type": "decision", "id": "d-1"},
        action="seal",
    )
    response = adapter.evaluate(request)
    assert response.decision is Decision.PERMIT


def test_static_policy_adapter_denies_missing_role():
    adapter = StaticPolicyAdapter(
        role_permissions={"sealer": [("decision", "seal")]}
    )
    request = PolicyEvalRequest(
        subject={"id": "user-1", "roles": ["viewer"]},
        resource={"type": "decision", "id": "d-1"},
        action="seal",
    )
    response = adapter.evaluate(request)
    assert response.decision is Decision.DENY


def test_policy_eval_request_defaults():
    request = PolicyEvalRequest(
        subject={"id": "user-1"},
        resource={"type": "decision"},
        action="read",
    )
    assert request.environment == {}


def test_policy_eval_response_decision_enum():
    response = PolicyEvalResponse(decision=Decision.INDETERMINATE, reason="missing data")
    assert response.decision == "indeterminate"


def test_eval_request_schema_has_required_fields():
    schema = _load_schema("policy-eval-request-schema.json")
    required = schema.get("required", [])
    assert set(required) >= {"subject", "resource", "action"}


def test_eval_response_schema_has_decision_enum():
    schema = _load_schema("policy-eval-response-schema.json")
    decision = schema["properties"]["decision"]
    assert decision["enum"] == ["permit", "deny", "indeterminate"]


def test_role_schema_has_required_fields():
    schema = _load_schema("role-schema.json")
    required = schema.get("required", [])
    assert "role_id" in required
    assert "permissions" in required
