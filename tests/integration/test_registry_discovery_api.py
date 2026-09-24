"""Integration tests for the Platform Registry and Capability Discovery APIs."""
import pytest
from fastapi.testclient import TestClient

from adapters.discovery.discovery_adapter import (
    InMemoryCapabilityRegistry,
    InMemoryServiceRegistry,
    SqlCapabilityRegistry,
    SqlServiceRegistry,
)
from sdk.common.persistence import PlatformStore
from services.capability_discovery.src.main import create_app as create_discovery_app
from services.platform_registry.src.main import create_app as create_registry_app

SERVICE = {
    "name": "flow-api",
    "product": "arca-flow",
    "version": "1.4.0",
    "endpoint": "http://flow:8010",
    "contracts": ["contracts/flow/openapi.yaml"],
}

CAPABILITY = {
    "id": "flow.approval.submit",
    "name": "Submit approval",
    "product": "arca-flow",
    "version": "1.4.0",
    "input_schema": "schemas/flow/approval-request.json",
    "output_schema": "schemas/flow/approval-response.json",
    "required_contracts": ["contracts/policy/"],
}


@pytest.mark.parametrize("backend", ["memory"])
def test_registry_api_roundtrip(backend):
    client = TestClient(create_registry_app(registry=InMemoryServiceRegistry()))
    _assert_registry_roundtrip(client)


def test_registry_api_roundtrip_sql(tmp_path):
    url = f"sqlite:///{tmp_path}/registry.db"
    client = TestClient(create_registry_app(registry=SqlServiceRegistry(PlatformStore(url))))
    _assert_registry_roundtrip(client)


def _assert_registry_roundtrip(client: TestClient) -> None:
    r = client.post("/v1/registry/services", json=SERVICE)
    assert r.status_code == 200 and r.json()["key"] == "arca-flow:flow-api"

    listed = client.get("/v1/registry/services").json()["services"]
    assert listed == [SERVICE]

    filtered = client.get("/v1/registry/services", params={"product": "other"})
    assert filtered.json()["services"] == []

    one = client.get("/v1/registry/services/arca-flow/flow-api")
    assert one.status_code == 200 and one.json()["endpoint"] == "http://flow:8010"

    assert client.get("/v1/registry/services/arca-flow/nope").status_code == 404
    assert client.get("/healthz").json() == {"status": "healthy"}


def test_registry_sql_mode_persists_across_restarts(tmp_path):
    url = f"sqlite:///{tmp_path}/registry.db"
    backend = SqlServiceRegistry(PlatformStore(url))
    TestClient(create_registry_app(registry=backend)).post(
        "/v1/registry/services", json=SERVICE
    )
    # New process: a fresh store over the same file must see the descriptor.
    reloaded = SqlServiceRegistry(PlatformStore(url))
    client = TestClient(create_registry_app(registry=reloaded))
    assert client.get("/v1/registry/services/arca-flow/flow-api").status_code == 200


@pytest.mark.parametrize(
    "make_registry",
    [
        InMemoryCapabilityRegistry,
        lambda: SqlCapabilityRegistry(PlatformStore("sqlite:///:memory:")),
    ],
    ids=["memory", "sql"],
)
def test_discovery_api_roundtrip(make_registry):
    client = TestClient(create_discovery_app(registry=make_registry()))

    r = client.post("/v1/capabilities", json=CAPABILITY)
    assert r.status_code == 200 and r.json()["id"] == "flow.approval.submit"

    results = client.get("/v1/capabilities").json()["capabilities"]
    assert results == [CAPABILITY]

    by_product = client.get("/v1/capabilities", params={"product": "arca-flow"})
    assert len(by_product.json()["capabilities"]) == 1
    by_contract = client.get(
        "/v1/capabilities", params={"contract": "contracts/policy/"}
    )
    assert len(by_contract.json()["capabilities"]) == 1
    miss = client.get("/v1/capabilities", params={"contract": "contracts/audit/"})
    assert miss.json()["capabilities"] == []


def test_discovery_register_is_idempotent_upsert():
    client = TestClient(create_discovery_app(registry=InMemoryCapabilityRegistry()))
    client.post("/v1/capabilities", json=CAPABILITY)
    updated = {**CAPABILITY, "version": "1.5.0"}
    client.post("/v1/capabilities", json=updated)
    results = client.get("/v1/capabilities").json()["capabilities"]
    assert results == [updated]
