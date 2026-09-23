"""Ontology gates for Turtle artifacts: syntax + SHACL semantic contracts.

The SHACL approach is empirically verified against the real pack ontologies
(morocco / france sovereignty):

  pyshacl.validate(data_graph=submitted, shacl_graph=shapes,
                   ont_graph=core_background, inference="rdfs",
                   abort_on_first=False)

Advanced mode is intentionally NOT enabled — the SPARQL constraints in the
ArcaQ contract shapes are evaluated anyway (verified empirically).

CRITICAL: only validation results whose focus node is IN THE SUBMITTED data
graph are attributed to the artifact. The core background graph (arcaq core +
governance instances, e.g. arcaq:Jurisdiction_MA which lacks belongsToDomain)
also gets validated and produces results that are not the artifact's fault;
those are filtered out.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import pyshacl
from rdflib import Graph
from rdflib.namespace import RDF, SH

from . import GateCheck, GateReport

logger = logging.getLogger(__name__)

SEMANTIC_CONTRACTS_SHAPE = "arcaq-semantic-contracts.shacl.ttl"
CORE_BACKGROUND_FILES = ("arcaq-core.ttl", "arcaq-governance-data.ttl")


@lru_cache(maxsize=1)
def _load_graphs(shapes_dir: str) -> tuple[Graph, Graph]:
    """Load the bundled SHACL shapes and merged core background graph once."""
    base = Path(shapes_dir)
    shapes = Graph()
    shapes.parse(base / SEMANTIC_CONTRACTS_SHAPE, format="turtle")
    core = Graph()
    for name in CORE_BACKGROUND_FILES:
        core.parse(base / name, format="turtle")
    return shapes, core


def validate_ontology_ttl(content: str, shapes_dir: str) -> GateReport:
    """Run the turtle-syntax and shacl-contracts gates on a Turtle artifact."""
    report = GateReport()

    # Gate 1: turtle-syntax — the artifact must at least be parseable RDF.
    data = Graph()
    try:
        data.parse(data=content, format="turtle")
    except Exception as exc:  # rdflib raises several parse error types
        report.checks.append(
            GateCheck(
                gate="turtle-syntax",
                passed=False,
                severity="violation",
                message=f"Turtle parsing failed: {exc}",
            )
        )
        return report  # no point running SHACL on unparseable data
    report.checks.append(
        GateCheck(
            gate="turtle-syntax",
            passed=True,
            severity="violation",
            message=f"Turtle parsed successfully ({len(data)} triples).",
        )
    )

    # Gate 2: shacl-contracts — the ArcaQ semantic quality gates.
    shapes, core_background = _load_graphs(shapes_dir)
    try:
        _conforms, report_graph, _text = pyshacl.validate(
            data_graph=data,
            shacl_graph=shapes,
            ont_graph=core_background,
            inference="rdfs",
            abort_on_first=False,
        )
    except Exception as exc:  # noqa: BLE001 — a crashed engine is a violation
        report.checks.append(
            GateCheck(
                gate="shacl-contracts",
                passed=False,
                severity="violation",
                message=f"SHACL validation engine error: {exc}",
            )
        )
        return report

    violations = 0
    for result in report_graph.subjects(RDF.type, SH.ValidationResult):
        focus = next(report_graph.objects(result, SH.focusNode), None)
        if focus is not None and not _in_graph(focus, data):
            # Focus node only exists in the core background graph (e.g.
            # arcaq:Jurisdiction_MA): not the submitted artifact's fault.
            continue
        severity_uri = next(report_graph.objects(result, SH.resultSeverity), SH.Violation)
        severity = "violation" if severity_uri == SH.Violation else "warning"
        messages = [
            str(m)
            for m in report_graph.objects(result, SH.resultMessage)
        ]
        message = "; ".join(messages) or "SHACL constraint violated."
        if focus is not None:
            message = f"{message} (focus: {focus})"
        passed = severity == "warning"
        if not passed:
            violations += 1
        report.checks.append(
            GateCheck(
                gate="shacl-contracts",
                passed=passed,
                severity=severity,
                message=message,
            )
        )

    if violations == 0:
        report.checks.append(
            GateCheck(
                gate="shacl-contracts",
                passed=True,
                severity="violation",
                message="All semantic contracts satisfied for this artifact.",
            )
        )
    return report


def _in_graph(node, graph: Graph) -> bool:
    """True when the node is a SUBJECT of the graph.

    Focus nodes that merely appear as objects (e.g. the artifact references
    arcaq:Jurisdiction_MA) are still core-background instances, not artifact
    statements — only subject membership attributes a result to the artifact.
    """
    return (node, None, None) in graph
