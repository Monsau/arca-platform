"""Validation gates — one module per artifact kind.

A gate never raises into the request flow: every outcome is expressed as check
entries (gate, passed, severity, message) so the caller gets an explicit,
auditable quality-gate report.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateCheck:
    """One entry of the quality-gate report."""

    gate: str
    passed: bool
    severity: str  # "violation" | "warning"
    message: str

    def as_dict(self) -> dict:
        return {
            "gate": self.gate,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class GateReport:
    """Aggregated outcome of all gates applied to one artifact."""

    checks: list[GateCheck] = field(default_factory=list)
    normalized: str | None = None

    @property
    def valid(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def detail(self) -> str:
        failed = [c for c in self.checks if not c.passed]
        if not failed:
            return "content conforms to the Suite contracts"
        parts = [f"{c.gate}: {c.message}" for c in failed[:5]]
        suffix = f" (+{len(failed) - 5} more)" if len(failed) > 5 else ""
        return "; ".join(parts) + suffix
