"""Unit tests for the reference lifecycle adapter (in-memory and SQL)."""
import pytest

from adapters.lifecycle.lifecycle_adapter import (
    IllegalTransitionError,
    InMemoryLifecycleAdapter,
    LifecycleState,
    SqlLifecycleAdapter,
)
from sdk.common.persistence import PlatformStore


def _walk(adapter, product="arca-flow", instance="pod-1"):
    adapter.transition(product, instance, LifecycleState.STARTING, "boot", "c-1")
    adapter.transition(product, instance, LifecycleState.READY, "serving", "c-2")


def test_happy_path_and_history():
    adapter = InMemoryLifecycleAdapter()
    _walk(adapter)
    assert adapter.current("arca-flow", "pod-1") == LifecycleState.READY
    history = adapter.history("arca-flow", "pod-1")
    assert [e["to_state"] for e in history] == ["starting", "ready"]
    assert history[0]["from_state"] == "registered"


def test_illegal_transition_rejected():
    adapter = InMemoryLifecycleAdapter()
    with pytest.raises(IllegalTransitionError):
        adapter.transition("p", "i", LifecycleState.READY, "skip", "c-1")


def test_degraded_then_ready():
    adapter = InMemoryLifecycleAdapter()
    adapter.transition("p", "i", LifecycleState.STARTING, "boot", "c-1")
    adapter.transition("p", "i", LifecycleState.DEGRADED, "db slow", "c-2")
    adapter.transition("p", "i", LifecycleState.READY, "recovered", "c-3")
    assert adapter.current("p", "i") == LifecycleState.READY


def test_sql_adapter_matches_memory_semantics():
    adapter = SqlLifecycleAdapter(PlatformStore("sqlite:///:memory:"))
    _walk(adapter)
    assert adapter.current("arca-flow", "pod-1") == LifecycleState.READY
    assert [e["to_state"] for e in adapter.history("arca-flow", "pod-1")] == [
        "starting",
        "ready",
    ]
    with pytest.raises(IllegalTransitionError):
        adapter.transition("arca-flow", "pod-1", LifecycleState.READY, "again", "c-3")


def test_sql_boot_migration_idempotent():
    store = PlatformStore("sqlite:///:memory:")
    adapter = SqlLifecycleAdapter(store)
    adapter2 = SqlLifecycleAdapter(store)  # second boot must not raise
    assert adapter2.current("p", "i") == LifecycleState.REGISTERED
