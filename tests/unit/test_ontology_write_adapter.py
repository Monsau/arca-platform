"""Tests for the ontology write adapter (Suite -> ArcaQ change proposals).

Covers (per EPICS.md golden rule #2 and EP-09 acceptance criteria):
  - Null adapter: disabled by default, no network call, no exception;
  - Http adapter: contract payload validated, entry_point forced to "suite",
    caller Authorization header forwarded verbatim;
  - graceful degradation: transport failure returns a degraded result and
    never raises into the business flow.

Falsification: captured-request assertions prove that no payload can reach
ArcaQ through this adapter without entry_point == "suite" and that identity
propagation cannot be silently dropped.
"""

import json
from pathlib import Path

import httpx
import pytest

from adapters.ontology.arcaq_ontology_adapter import (
    CHANGE_PROPOSALS_ENDPOINT,
    SUITE_ENTRY_POINT,
    ArcaqOntologyWriteAdapter,
    NullOntologyWriteAdapter,
    OntologyChangeProposal,
    OntologyWriteAdapter,
)

SCHEMAS_DIR = Path(__file__).parents[2] / "schemas" / "ontology"

PROPOSAL = OntologyChangeProposal(
    change_type="add_class",
    concept_uri="http://arcaq.com/ontology#FrenchDataTrust",
    impact_level="minor",
    description="Introduce the FrenchDataTrust concept",
    proposed_ttl="@prefix arcaq: <http://arcaq.com/ontology#> .\narcaq:FrenchDataTrust a owl:Class .",
)


def _capture_transport():
    """Return a MockTransport plus the list that captures (request, body)."""
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request, json.loads(request.content)))
        return httpx.Response(
            201,
            json={
                "id": "cp-1",
                "change_type": "add_class",
                "concept_uri": PROPOSAL.concept_uri,
                "impact_level": "minor",
                "description": PROPOSAL.description,
                "proposer": "suite-caller",
                "state": "draft",
                "proposed_at": "2026-09-21T00:00:00Z",
                "entry_point": SUITE_ENTRY_POINT,
                "ttl_validation": {"status": "passed", "syntax_ok": True},
            },
        )

    return httpx.MockTransport(handler), captured


def _adapter(transport: httpx.MockTransport) -> ArcaqOntologyWriteAdapter:
    client = httpx.Client(
        base_url="http://arcaq.internal", transport=transport, timeout=5.0
    )
    return ArcaqOntologyWriteAdapter(base_url="http://arcaq.internal", client=client)


# ── Protocol / Null ──────────────────────────────────────────────────────────


def test_null_adapter_is_disabled_and_never_raises():
    adapter = NullOntologyWriteAdapter()
    assert isinstance(adapter, OntologyWriteAdapter)  # structural conformance

    result = adapter.submit_change(PROPOSAL, authorization="Bearer abc")
    assert result.submitted is False
    assert result.status == "disabled"
    assert result.proposal_id is None
    # Provenance vocabulary stays consistent even when disabled.
    assert result.entry_point == SUITE_ENTRY_POINT


def test_default_settings_select_null_adapter():
    from sdk.common.config import PlatformSettings

    settings = PlatformSettings()
    assert settings.ontology_write_adapter == "null"


def test_null_adapter_validates_before_returning():
    adapter = NullOntologyWriteAdapter()
    with pytest.raises(ValueError):
        adapter.submit_change(
            OntologyChangeProposal(
                change_type="nuke_everything",
                concept_uri="http://arcaq.com/ontology#X",
                impact_level="major",
                description="Invalid change type",
            )
        )


# ── Http adapter — contract and provenance ───────────────────────────────────


def test_http_submits_contract_payload_with_suite_entry_point():
    transport, captured = _capture_transport()
    adapter = _adapter(transport)

    result = adapter.submit_change(PROPOSAL, authorization="Bearer caller-jwt")

    assert result.submitted is True
    assert result.status == "created"
    assert result.proposal_id == "cp-1"
    assert result.entry_point == SUITE_ENTRY_POINT

    (request, body) = captured[0]
    assert request.url.path == CHANGE_PROPOSALS_ENDPOINT
    # Falsification: the endpoint path is the centralized write funnel only.
    assert body["entry_point"] == "suite"
    assert body["change_type"] == "add_class"
    assert body["concept_uri"] == PROPOSAL.concept_uri
    assert body["impact_level"] == "minor"
    assert body["proposed_ttl"].startswith("@prefix arcaq:")


def test_http_forwards_caller_authorization_verbatim():
    transport, captured = _capture_transport()
    adapter = _adapter(transport)

    adapter.submit_change(PROPOSAL, authorization="Bearer eyJhbGciOiJ...")

    (request, _body) = captured[0]
    # Identity propagation: the Suite never rewrites or replaces the
    # caller's credentials — ArcaQ's central PDP resolves permissions.
    assert request.headers["Authorization"] == "Bearer eyJhbGciOiJ..."


def test_http_omits_auth_header_when_no_identity_provided():
    transport, captured = _capture_transport()
    adapter = _adapter(transport)

    adapter.submit_change(PROPOSAL)

    (request, _body) = captured[0]
    assert "Authorization" not in request.headers


def test_http_sends_explicit_proposer_when_given():
    transport, captured = _capture_transport()
    adapter = _adapter(transport)

    proposal = OntologyChangeProposal(
        change_type="modify_label",
        concept_uri="http://arcaq.com/ontology#Jurisdiction_FR",
        impact_level="patch",
        description="Fix a French label",
        proposer="alice@example.org",
    )
    adapter.submit_change(proposal)

    (_request, body) = captured[0]
    assert body["proposer"] == "alice@example.org"


def test_http_drops_null_optional_fields():
    transport, captured = _capture_transport()
    adapter = _adapter(transport)

    minimal = OntologyChangeProposal(
        change_type="deprecate",
        concept_uri="http://arcaq.com/ontology#LegacyConcept",
        impact_level="major",
        description="Deprecate the legacy concept",
    )
    adapter.submit_change(minimal)

    (_request, body) = captured[0]
    assert "proposed_ttl" not in body
    assert "proposer" not in body


# ── Http adapter — failure semantics ─────────────────────────────────────────


def test_http_degrades_on_transport_error_without_raising():
    def failing_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("arcaq unreachable", request=request)

    transport = httpx.MockTransport(failing_handler)
    adapter = _adapter(transport)

    result = adapter.submit_change(PROPOSAL, authorization="Bearer abc")

    assert result.submitted is False
    assert result.status == "degraded"
    assert "unreachable" in result.detail
    assert result.entry_point == SUITE_ENTRY_POINT


def test_http_maps_rejection_status():
    transport = httpx.MockTransport(
        lambda _req: httpx.Response(422, json={"detail": "invalid Turtle"})
    )
    adapter = _adapter(transport)

    result = adapter.submit_change(PROPOSAL)

    assert result.submitted is False
    assert result.status == "rejected"
    assert "422" in result.detail


def test_proposal_validate_rejects_out_of_vocab_values():
    with pytest.raises(ValueError):
        OntologyChangeProposal(
            change_type="add_class",
            concept_uri="http://arcaq.com/ontology#X",
            impact_level="catastrophic",
            description="Invalid impact level",
        ).validate()


def test_proposal_validate_rejects_short_description():
    with pytest.raises(ValueError):
        OntologyChangeProposal(
            change_type="add_class",
            concept_uri="http://arcaq.com/ontology#X",
            impact_level="minor",
            description="abc",
        ).validate()


# ── Contract schema sanity (same discipline as test_policy_adapter.py) ───────


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


def test_request_schema_enforces_suite_entry_point_vocabulary():
    schema = _load_schema("change-proposal-request-schema.json")
    entry_point = schema["properties"]["entry_point"]
    assert entry_point["enum"] == ["direct", "suite"]
    for field in ("change_type", "concept_uri", "impact_level", "description"):
        assert field in schema["required"]


def test_response_schema_mirrors_write_funnel_fields():
    schema = _load_schema("change-proposal-response-schema.json")
    for field in ("id", "state", "proposer", "entry_point"):
        assert field in schema["required"]
    # ttl_validation is Optional on the ArcaQ model (absent until validated).
    assert "ttl_validation" in schema["properties"]
    assert schema["properties"]["entry_point"]["enum"] == ["direct", "suite"]
