"""Capability Discovery API.

Products query this API to discover platform capabilities and the contracts
required to use them.

Persistence: in-memory by default (tests, local development); SQL-backed
(SQLite/PostgreSQL) with an idempotent boot migration when
``ARCA_DISCOVERY_BACKEND=sql`` — the store URL comes from
``ARCA_DISCOVERY_DATABASE_URL``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from adapters.discovery.discovery_adapter import (
    CapabilityRegistry,
    InMemoryCapabilityRegistry,
    SqlCapabilityRegistry,
)
from sdk.common.persistence import PlatformStore


class Capability(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    input_schema: str = Field(..., min_length=1)
    output_schema: str = Field(..., min_length=1)
    required_contracts: list[str] = Field(default_factory=list)


def default_registry() -> CapabilityRegistry:
    """Registry backend from the environment: memory (default) or sql."""
    if os.getenv("ARCA_DISCOVERY_BACKEND", "memory") == "sql":
        url = os.getenv("ARCA_DISCOVERY_DATABASE_URL", "sqlite:///./arca_discovery.db")
        return SqlCapabilityRegistry(PlatformStore(url))
    return InMemoryCapabilityRegistry()


def create_app(registry: CapabilityRegistry | None = None) -> FastAPI:
    """App factory — inject a registry store for tests or non-default backends."""
    registry = registry or default_registry()
    app = FastAPI(title="Arca Capability Discovery API", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "healthy"}

    @app.post("/v1/capabilities")
    def register_capability(cap: Capability) -> dict:
        cap_id = registry.register(cap.model_dump())
        return {"status": "registered", "id": cap_id}

    @app.get("/v1/capabilities")
    def search_capabilities(
        product: str | None = Query(default=None),
        contract: str | None = Query(default=None),
    ) -> dict:
        return {"capabilities": registry.search(product=product, contract=contract)}

    return app


# Module-level app for `uvicorn services.capability_discovery.src.main:app`.
app = create_app()
