"""Ontology gates: syntax, SHACL contracts, real pack ontologies, fixtures."""
from __future__ import annotations

from pathlib import Path

PACKS_ROOT = Path(r"C:\projets\innovation\arca-packs")
MOROCCO_TTL = PACKS_ROOT / "src" / "packs" / "morocco-sovereignty" / "ontology" / "sovereignty-ma.ttl"
FRANCE_TTL = PACKS_ROOT / "src" / "packs" / "france-sovereignty" / "ontology" / "sovereignty-fr.ttl"

MONOLINGUAL_CLASS_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .

ex:Thing a owl:Class ;
    rdfs:label "Thing"@en ;
    rdfs:comment "A thing."@en .
"""

BROKEN_TTL = "@prefix ex: <http://ex.org/> .\nex:a ex:b ex:c"  # missing final dot


def _validate(authed_client, content):
    resp = authed_client.post(
        "/api/v1/validate",
        json={"artifact_kind": "ontology_ttl", "content": content},
    )
    assert resp.status_code == 200
    return resp.json()


def test_invalid_turtle_fails_syntax_gate(authed_client):
    body = _validate(authed_client, BROKEN_TTL)
    assert body["valid"] is False
    syntax = [c for c in body["checks"] if c["gate"] == "turtle-syntax"]
    assert len(syntax) == 1
    assert syntax[0]["passed"] is False
    assert syntax[0]["severity"] == "violation"
    # shacl-contracts must not run on unparseable data
    assert [c for c in body["checks"] if c["gate"] == "shacl-contracts"] == []


def test_valid_turtle_reports_triple_count(authed_client):
    body = _validate(
        authed_client,
        '@prefix ex: <http://ex.org/> .\nex:a ex:b ex:c .\nex:a ex:b ex:d .\n',
    )
    assert body["valid"] is True
    syntax = next(c for c in body["checks"] if c["gate"] == "turtle-syntax")
    assert syntax["passed"] is True
    assert "2 triples" in syntax["message"]


def test_monolingual_class_fails_with_french_label_message(authed_client):
    """A class with only an @en label must fail, mentioning the French label."""
    body = _validate(authed_client, MONOLINGUAL_CLASS_TTL)
    assert body["valid"] is False
    failed = [c for c in body["checks"] if c["gate"] == "shacl-contracts" and not c["passed"]]
    assert failed, body
    assert any("French" in c["message"] or "@fr" in c["message"] for c in failed)


def test_monolingual_warning_is_reported_but_does_not_fail(authed_client):
    """The missing rdfs:comment is a sh:Warning: reported, but valid stays tied
    to violations only. The class is otherwise fully conformant (en+fr labels)
    so the ONLY failing gate would be the warning itself."""
    content = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .
ex:Thing a owl:Class ;
    rdfs:label "Thing"@en ;
    rdfs:label "Truc"@fr .
"""
    body = _validate(authed_client, content)
    assert body["valid"] is True, body["detail"]
    warnings = [c for c in body["checks"] if c["severity"] == "warning"]
    assert any("rdfs:comment" in c["message"] for c in warnings)
    assert all(c["passed"] for c in warnings)


def test_real_morocco_ontology_is_valid(authed_client):
    assert MOROCCO_TTL.exists(), f"fixture missing: {MOROCCO_TTL}"
    body = _validate(authed_client, MOROCCO_TTL.read_text(encoding="utf-8"))
    assert body["valid"] is True, body["detail"]


def test_real_france_ontology_is_valid(authed_client):
    """France has in-graph warnings (orphan individuals) but no violations:
    valid must stay true."""
    assert FRANCE_TTL.exists(), f"fixture missing: {FRANCE_TTL}"
    body = _validate(authed_client, FRANCE_TTL.read_text(encoding="utf-8"))
    assert body["valid"] is True, body["detail"]
    warnings = [c for c in body["checks"] if c["severity"] == "warning"]
    assert warnings  # the orphan-individual warnings are expected here
    assert all(c["passed"] for c in warnings)


def test_focus_node_filtering_ignores_core_background_violations(authed_client):
    """Jurisdiction_MA lacks belongsToDomain but is a core instance, not the
    artifact's fault: a minimal valid artifact must not inherit that violation."""
    body = _validate(
        authed_client,
        """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <http://example.org/> .
ex:Widget a owl:Class ;
    rdfs:label "Widget"@en ;
    rdfs:label "Gadget"@fr ;
    rdfs:comment "A widget."@en .
""",
    )
    assert body["valid"] is True, body["detail"]
