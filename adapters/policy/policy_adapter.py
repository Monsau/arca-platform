"""Reference policy adapter for the Arca Platform policy contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class Decision(str, Enum):
    PERMIT = "permit"
    DENY = "deny"
    INDETERMINATE = "indeterminate"


@dataclass
class PolicyEvalRequest:
    subject: dict[str, Any]
    resource: dict[str, Any]
    action: str
    environment: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyEvalResponse:
    decision: Decision
    reason: str = ""
    obligations: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class PolicyAdapter(Protocol):
    """Neutral interface for policy evaluation."""

    def evaluate(self, request: PolicyEvalRequest) -> PolicyEvalResponse:
        ...


class NullPolicyAdapter:
    """Default adapter when no policy engine is configured.

    Denies every request unless explicitly configured to permit all.
    """

    def __init__(self, default_decision: Decision = Decision.DENY) -> None:
        self.default_decision = default_decision

    def evaluate(self, request: PolicyEvalRequest) -> PolicyEvalResponse:
        return PolicyEvalResponse(
            decision=self.default_decision,
            reason="null policy adapter: no policy engine configured",
        )


class StaticPolicyAdapter:
    """In-memory role-based adapter for tests and local development.

    Maps roles to (resource_type, action) pairs. A request is permitted if the
    subject has a role granting the requested action on the resource type.
    """

    def __init__(self, role_permissions: dict[str, list[tuple[str, str]]] | None = None) -> None:
        self.role_permissions = role_permissions or {}

    def evaluate(self, request: PolicyEvalRequest) -> PolicyEvalResponse:
        resource_type = request.resource.get("type", "")
        roles = request.subject.get("roles", [])
        for role in roles:
            for rt, action in self.role_permissions.get(role, []):
                if rt == resource_type and action == request.action:
                    return PolicyEvalResponse(
                        decision=Decision.PERMIT,
                        reason=f"role '{role}' grants {action} on {resource_type}",
                    )
        return PolicyEvalResponse(
            decision=Decision.DENY,
            reason=f"no role grants {request.action} on {resource_type}",
        )
