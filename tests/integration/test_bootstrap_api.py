import pytest
from fastapi.testclient import TestClient

from services.bootstrap.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_healthz(client: TestClient):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_and_list_products(client: TestClient):
    response = client.post(
        "/v1/bootstrap/register",
        json={"product": "arca-flow", "version": "0.2.0", "contracts": ["events-v1"]},
    )
    assert response.status_code == 200
    response = client.get("/v1/bootstrap/products")
    data = response.json()
    assert any(p["product"] == "arca-flow" for p in data["products"])
