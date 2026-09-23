"""Workflow gates: schema sanity + legacy-key normalization.

Legacy keys are normalized, never silently accepted: sla_minutes becomes
sla_seconds (x60) and retry.max_attempts becomes retry.max_retries. Every
rename is reported as a warning check entry and the fully normalized YAML is
returned in the response `normalized` field (null when nothing had to change).
"""
from __future__ import annotations

import copy

import yaml

from . import GateCheck, GateReport

GATE_SCHEMA = "workflow-schema"
GATE_NORMALIZATION = "workflow-normalization"


def validate_workflow_yaml(content: str) -> GateReport:
    """Run the workflow-schema and workflow-normalization gates."""
    report = GateReport()

    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        report.checks.append(
            GateCheck(
                gate=GATE_SCHEMA,
                passed=False,
                severity="violation",
                message=f"workflow is not valid YAML: {exc}",
            )
        )
        return report
    if not isinstance(doc, dict):
        report.checks.append(
            GateCheck(
                gate=GATE_SCHEMA,
                passed=False,
                severity="violation",
                message=f"workflow must be a mapping at the top level, got {type(doc).__name__}.",
            )
        )
        return report

    workflow_id = doc.get("id")
    steps = doc.get("steps")
    schema_errors: list[str] = []
    if not workflow_id:
        schema_errors.append("workflow must define an 'id'.")
    if not isinstance(steps, list) or not steps:
        schema_errors.append("workflow must define 'steps' as a non-empty list.")
    for err in schema_errors:
        report.checks.append(
            GateCheck(
                gate=GATE_SCHEMA,
                passed=False,
                severity="violation",
                message=err,
            )
        )
    if schema_errors:
        return report  # cannot normalize a structurally broken workflow
    report.checks.append(
        GateCheck(
            gate=GATE_SCHEMA,
            passed=True,
            severity="violation",
            message=f"Workflow schema satisfied ({len(steps)} steps).",
        )
    )

    # Normalization operates on a copy; the original document is never mutated.
    normalized = copy.deepcopy(doc)
    renames = 0
    for index, step in enumerate(normalized["steps"]):
        if not isinstance(step, dict):
            continue
        label = step.get("id") or step.get("name") or f"step #{index}"
        if "sla_minutes" in step:
            minutes = step.pop("sla_minutes")
            try:
                step["sla_seconds"] = int(minutes) * 60
            except (TypeError, ValueError):
                step["sla_seconds"] = minutes  # keep as-is; schema gate owns typing
            renames += 1
            report.checks.append(
                GateCheck(
                    gate=GATE_NORMALIZATION,
                    passed=True,
                    severity="warning",
                    message=(
                        f"{label}: legacy key 'sla_minutes' renamed to "
                        f"'sla_seconds' (value x60)."
                    ),
                )
            )
        retry = step.get("retry")
        if isinstance(retry, dict) and "max_attempts" in retry:
            retry["max_retries"] = retry.pop("max_attempts")
            renames += 1
            report.checks.append(
                GateCheck(
                    gate=GATE_NORMALIZATION,
                    passed=True,
                    severity="warning",
                    message=(
                        f"{label}: legacy key 'retry.max_attempts' renamed to "
                        f"'retry.max_retries'."
                    ),
                )
            )

    if renames:
        report.normalized = yaml.safe_dump(normalized, sort_keys=True)
    report.checks.append(
        GateCheck(
            gate=GATE_NORMALIZATION,
            passed=True,
            severity="violation",
            message=(
                f"{renames} legacy key(s) normalized."
                if renames
                else "No legacy keys; workflow already uses canonical keys."
            ),
        )
    )
    return report
