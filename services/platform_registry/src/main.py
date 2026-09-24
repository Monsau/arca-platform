"""Platform Registry API.

Stores platform-level metadata and service descriptors so that products and
adapters can discover each other without hard-coding endpoints.

Persistence: in-memory by default (tests, local development); SQL-backed
(SQLite/PostgreSQL) with an idempotent boot migration when
``ARCA_REGISTRY_BACKEND=sql`` — the store URL comes from
``ARCA_REGISTRY_DATABASE_URL``.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from adapters.discovery.discovery_adapter import (
    InMemoryServiceRegistry,
    ServiceRegistry,
    SqlServiceRegistry,
)
from sdk.common.persistence import PlatformStore


class ServiceDescriptor(BaseModel):
    name: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    health_endpoint: str = Field(default="/healthz")
    contracts: list[str] = Field(default_factory=list)


def default_registry() -> ServiceRegistry:
    """Registry backend from the environment: memory (default) or sql."""
    if os.getenv("ARCA_REGISTRY_BACKEND", "memory") == "sql":
        url = os.getenv("ARCA_REGISTRY_DATABASE_URL", "sqlite:///./arca_registry.db")
        return SqlServiceRegistry(PlatformStore(url))
    return InMemoryServiceRegistry()


def create_app(registry: ServiceRegistry | None = None) -> FastAPI:
    """App factory — inject a registry store for tests or non-default backends."""
    registry = registry or default_registry()
    app = FastAPI(title="Arca Platform Registry API", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "healthy"}

    @app.post("/v1/registry/services")
    def register_service(descriptor: ServiceDescriptor) -> dict:
        # Store exactly what the caller declared (validated fields only), so a
        # register -> list/get roundtrip returns the posted document verbatim.
        key = registry.register(descriptor.model_dump(exclude_unset=True))
        return {"status": "registered", "key": key}

    @app.get("/v1/registry/services")
    def list_services(product: str | None = None) -> dict:
        return {"services": registry.list(product=product)}

    @app.get("/v1/registry/services/{product}/{name}")
    def get_service(product: str, name: str) -> dict:
        descriptor = registry.get(product, name)
        if descriptor is None:
            raise HTTPException(status_code=404, detail="Service not found")
        return descriptor

    return app


# Module-level app for `uvicorn services.platform_registry.src.main:app`.
app = create_app()
