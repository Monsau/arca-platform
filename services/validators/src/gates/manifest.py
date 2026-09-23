"""OOC manifest gate — mirrors PackManifest.validate_schema in arca-packs.

The rules are duplicated here on purpose: the validators service is the
Suite-side quality gate, cross-module code imports are forbidden (contracts
only). Keep this in sync with
arca-packs/src/core/domain/manifest.py::PackManifest.validate_schema.
"""
from __future__ import annotations

import json
import re

import yaml

from . import GateCheck, GateReport

_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-+][0-9A-Za-z.\-]+)?$")
SUPPORTED_SUPPORT_MODELS = (None, "standard", "premium")


def validate_ooc_manifest(content: str, content_format: str | None) -> GateReport:
    """Run the manifest-schema gate on a JSON or YAML manifest."""
    report = GateReport()
    doc, parse_error = _parse(content, content_format)
    if parse_error is not None:
        report.checks.append(
            GateCheck(
                gate="manifest-schema",
                passed=False,
                severity="violation",
                message=parse_error,
            )
        )
        return report
    if not isinstance(doc, dict):
        report.checks.append(
            GateCheck(
                gate="manifest-schema",
                passed=False,
                severity="violation",
                message=f"manifest must be a mapping at the top level, got {type(doc).__name__}.",
            )
        )
        return report

    errors: list[str] = []
    pack_id = doc.get("pack_id")
    if not pack_id or not isinstance(pack_id, str) or not _PACK_ID_RE.match(pack_id):
        errors.append(f"invalid pack_id: {pack_id!r}")
    version = doc.get("version")
    if not version or not isinstance(version, str) or not _SEMVER_RE.match(version):
        errors.append(f"invalid semver version: {version!r}")
    metadata = doc.get("metadata") or {}
    if not isinstance(metadata, dict) or not metadata.get("owner"):
        errors.append("metadata.owner is required")
    support_model = metadata.get("support_model") if isinstance(metadata, dict) else None
    if support_model not in SUPPORTED_SUPPORT_MODELS:
        errors.append("metadata.support_model must be standard|premium")
    if not doc.get("artifacts"):
        errors.append("at least one artifact must be declared")

    if errors:
        for err in errors:
            report.checks.append(
                GateCheck(
                    gate="manifest-schema",
                    passed=False,
                    severity="violation",
                    message=err,
                )
            )
    else:
        report.checks.append(
            GateCheck(
                gate="manifest-schema",
                passed=True,
                severity="violation",
                message="Manifest satisfies the OOC schema rules.",
            )
        )
    return report


def _parse(content: str, content_format: str | None) -> tuple[object | None, str | None]:
    """Parse manifest content as JSON and/or YAML. Returns (doc, error)."""
    if content_format == "json":
        try:
            return json.loads(content), None
        except json.JSONDecodeError as exc:
            return None, f"manifest is not valid JSON: {exc}"
    if content_format == "yaml":
        try:
            return yaml.safe_load(content), None
        except yaml.YAMLError as exc:
            return None, f"manifest is not valid YAML: {exc}"
    # No explicit format: prefer JSON, fall back to YAML.
    try:
        return json.loads(content), None
    except json.JSONDecodeError as json_exc:
        try:
            return yaml.safe_load(content), None
        except yaml.YAMLError as yaml_exc:
            return None, (
                f"manifest is neither valid JSON ({json_exc}) nor valid YAML ({yaml_exc})"
            )
