"""Unit tests for the reference discovery adapter (in-memory and SQL)."""
from adapters.discovery.discovery_adapter import (
    InMemoryServiceRegistry,
    SqlServiceRegistry,
)
from sdk.common.persistence import PlatformStore

DESCRIPTOR = {
    "name": "flow-api",
    "product": "arca-flow",
    "version": "1.4.0",
    "endpoint": "http://flow:8010",
    "health_endpoint": "/healthz",
    "contracts": ["contracts/flow/openapi.yaml"],
}


def test_memory_register_list_get():
    registry = InMemoryServiceRegistry()
    key = registry.register(DESCRIPTOR)
    assert key == "arca-flow:flow-api"
    assert registry.get("arca-flow", "flow-api") == DESCRIPTOR
    assert registry.get("arca-flow", "nope") is None
    assert len(registry.list()) == 1
    assert registry.list(product="arca-flow") == [DESCRIPTOR]
    assert registry.list(product="other") == []


def test_memory_register_is_upsert():
    registry = InMemoryServiceRegistry()
    registry.register(DESCRIPTOR)
    updated = {**DESCRIPTOR, "version": "1.5.0"}
    registry.register(updated)
    assert registry.get("arca-flow", "flow-api")["version"] == "1.5.0"
    assert len(registry.list()) == 1


def test_sql_register_list_get():
    registry = SqlServiceRegistry(PlatformStore("sqlite:///:memory:"))
    registry.register(DESCRIPTOR)
    assert registry.get("arca-flow", "flow-api") == DESCRIPTOR
    assert registry.list(product="arca-flow") == [DESCRIPTOR]
    assert registry.list(product="other") == []


def test_sql_persists_across_instances():
    store = PlatformStore("sqlite:///:memory:")
    SqlServiceRegistry(store).register(DESCRIPTOR)
    # A new adapter over the same store sees the data (idempotent boot migration).
    reloaded = SqlServiceRegistry(store)
    assert reloaded.get("arca-flow", "flow-api") == DESCRIPTOR
