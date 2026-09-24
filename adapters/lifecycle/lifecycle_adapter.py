"""Reference lifecycle adapter for the Arca Platform lifecycle contract.

Tracks per-instance lifecycle states and transition events per
`contracts/lifecycle/`. Illegal transitions are rejected; every accepted
transition is recorded as a `LifecycleTransitionEvent`.

Backends: in-memory (default, for tests and local development) and SQL
(SQLite/PostgreSQL via `sdk/common/persistence.py`) with an idempotent
boot migration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable
from uuid import uuid4

from sqlalchemy import Column, MetaData, String, Table, select

from sdk.common.persistence import PlatformStore


class LifecycleState(str, Enum):
    REGISTERED = "registered"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


ALLOWED_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.REGISTERED: {LifecycleState.STARTING, LifecycleState.FAILED},
    LifecycleState.STARTING: {
        LifecycleState.READY,
        LifecycleState.DEGRADED,
        LifecycleState.FAILED,
    },
    LifecycleState.READY: {LifecycleState.DEGRADED, LifecycleState.STOPPING, LifecycleState.FAILED},
    LifecycleState.DEGRADED: {LifecycleState.READY, LifecycleState.STOPPING, LifecycleState.FAILED},
    LifecycleState.FAILED: {LifecycleState.STOPPING},
    LifecycleState.STOPPING: {LifecycleState.STOPPED},
    LifecycleState.STOPPED: set(),
}


class IllegalTransitionError(ValueError):
    """Raised when a transition is not in the contract's transition table."""


@runtime_checkable
class LifecycleAdapter(Protocol):
    """Neutral interface for lifecycle tracking."""

    def current(self, product: str, instance_id: str) -> LifecycleState:
        ...

    def transition(
        self,
        product: str,
        instance_id: str,
        to_state: LifecycleState,
        reason: str,
        correlation_id: str,
    ) -> dict:
        ...

    def history(self, product: str, instance_id: str) -> list[dict]:
        ...


def _event(
    product: str,
    instance_id: str,
    from_state: LifecycleState,
    to_state: LifecycleState,
    reason: str,
    correlation_id: str,
) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product": product,
        "instance_id": instance_id,
        "from_state": from_state.value,
        "to_state": to_state.value,
        "reason": reason,
        "correlation_id": correlation_id,
    }


class InMemoryLifecycleAdapter:
    """Default in-memory lifecycle adapter (tests, local development)."""

    def __init__(self) -> None:
        self._current: dict[tuple[str, str], LifecycleState] = {}
        self._history: dict[tuple[str, str], list[dict]] = {}

    def current(self, product: str, instance_id: str) -> LifecycleState:
        return self._current.get((product, instance_id), LifecycleState.REGISTERED)

    def transition(
        self,
        product: str,
        instance_id: str,
        to_state: LifecycleState,
        reason: str,
        correlation_id: str,
    ) -> dict:
        key = (product, instance_id)
        from_state = self.current(product, instance_id)
        if to_state not in ALLOWED_TRANSITIONS[from_state]:
            raise IllegalTransitionError(
                f"illegal transition {from_state.value} -> {to_state.value} "
                f"for {product}/{instance_id}"
            )
        event = _event(product, instance_id, from_state, to_state, reason, correlation_id)
        self._current[key] = to_state
        self._history.setdefault(key, []).append(event)
        return event

    def history(self, product: str, instance_id: str) -> list[dict]:
        return list(self._history.get((product, instance_id), []))


class SqlLifecycleAdapter:
    """SQL-backed lifecycle adapter with an idempotent boot migration."""

    def __init__(self, store: PlatformStore) -> None:
        self._store = store
        metadata = MetaData()
        self._states = Table(
            "lifecycle_states",
            metadata,
            Column("product", String(64), primary_key=True),
            Column("instance_id", String(128), primary_key=True),
            Column("state", String(32), nullable=False),
        )
        self._events = Table(
            "lifecycle_transitions",
            metadata,
            Column("id", String(64), primary_key=True),
            Column("product", String(64), nullable=False),
            Column("instance_id", String(128), nullable=False),
            Column("from_state", String(32), nullable=False),
            Column("to_state", String(32), nullable=False),
            Column("reason", String(256), nullable=False),
            Column("correlation_id", String(64), nullable=False),
            Column("timestamp", String(64), nullable=False),
        )
        # Idempotent boot migration — safe on every startup.
        self._store.ensure_schema(self._states, self._events)

    def current(self, product: str, instance_id: str) -> LifecycleState:
        with self._store.session() as s:
            row = s.execute(
                select(self._states.c.state).where(
                    self._states.c.product == product,
                    self._states.c.instance_id == instance_id,
                )
            ).first()
        return LifecycleState(row.state) if row else LifecycleState.REGISTERED

    def transition(
        self,
        product: str,
        instance_id: str,
        to_state: LifecycleState,
        reason: str,
        correlation_id: str,
    ) -> dict:
        from_state = self.current(product, instance_id)
        if to_state not in ALLOWED_TRANSITIONS[from_state]:
            raise IllegalTransitionError(
                f"illegal transition {from_state.value} -> {to_state.value} "
                f"for {product}/{instance_id}"
            )
        event = _event(product, instance_id, from_state, to_state, reason, correlation_id)
        event_id = f"{product}:{instance_id}:{uuid4().hex[:12]}"
        with self._store.session() as s:
            existing = s.execute(
                select(self._states).where(
                    self._states.c.product == product,
                    self._states.c.instance_id == instance_id,
                )
            ).first()
            if existing is None:
                s.execute(
                    self._states.insert().values(
                        product=product, instance_id=instance_id, state=to_state.value
                    )
                )
            else:
                s.execute(
                    self._states.update()
                    .where(
                        self._states.c.product == product,
                        self._states.c.instance_id == instance_id,
                    )
                    .values(state=to_state.value)
                )
            s.execute(
                self._events.insert().values(
                    id=event_id,
                    product=product,
                    instance_id=instance_id,
                    from_state=from_state.value,
                    to_state=to_state.value,
                    reason=reason,
                    correlation_id=correlation_id,
                    timestamp=event["timestamp"],
                )
            )
        return event

    def history(self, product: str, instance_id: str) -> list[dict]:
        with self._store.session() as s:
            rows = s.execute(
                select(self._events)
                .where(
                    self._events.c.product == product,
                    self._events.c.instance_id == instance_id,
                )
                .order_by(self._events.c.timestamp, self._events.c.id)
            ).all()
        return [
            {
                "timestamp": r.timestamp,
                "product": r.product,
                "instance_id": r.instance_id,
                "from_state": r.from_state,
                "to_state": r.to_state,
                "reason": r.reason,
                "correlation_id": r.correlation_id,
            }
            for r in rows
        ]
