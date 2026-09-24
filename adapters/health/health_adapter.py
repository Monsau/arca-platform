"""Reference health adapter for the Arca Platform health contract.

Wraps the shared `HealthRegistry` from `sdk/common/health.py` so platform
tooling consumes a single `report()` surface regardless of how a product
registers its checks.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sdk.common.health import HealthCheck, HealthRegistry


@runtime_checkable
class HealthAdapter(Protocol):
    """Neutral interface for product health reporting."""

    def report(self) -> dict:
        ...

    def check(self, name: str) -> dict | None:
        ...


class LocalHealthAdapter:
    """In-memory health adapter backed by the shared HealthRegistry."""

    def __init__(self, registry: HealthRegistry) -> None:
        self.registry = registry

    def register(self, fn) -> None:
        self.registry.register(fn)

    def report(self) -> dict:
        return self.registry.run().to_dict()

    def check(self, name: str) -> dict | None:
        for fn in self.registry._checks:  # read-only traversal of registered checks
            result: HealthCheck = fn()
            if result.name == name:
                return {
                    "status": result.status.value,
                    "message": result.message,
                    "details": result.details,
                }
        return None
