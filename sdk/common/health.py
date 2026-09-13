"""Arca Platform health, readiness and liveness conventions.

Products use this SDK to expose standardized health endpoints that platform
tooling can consume uniformly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class HealthReport:
    status: HealthStatus
    version: str
    checks: list[HealthCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "version": self.version,
            "checks": {
                check.name: {
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                }
                for check in self.checks
            },
        }


HealthCheckCallable = Callable[[], HealthCheck]


class HealthRegistry:
    """Register and run product health checks."""

    def __init__(self, version: str) -> None:
        self.version = version
        self._checks: list[HealthCheckCallable] = []

    def register(self, fn: HealthCheckCallable) -> HealthCheckCallable:
        self._checks.append(fn)
        return fn

    def run(self) -> HealthReport:
        checks = [fn() for fn in self._checks]
        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in checks):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        return HealthReport(status=status, version=self.version, checks=checks)
