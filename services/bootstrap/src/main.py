"""Platform Bootstrap API.

Products call this API at startup to register themselves and discover the
capabilities the platform exposes to them.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Arca Platform Bootstrap API", version="0.1.0")

# In-memory registries; production deployments use a persistent store.
_registered_products: dict[str, dict] = {}
_capabilities: list[dict] = []


class RegisterRequest(BaseModel):
    product: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    contracts: list[str] = Field(default_factory=list)


class CapabilityRegistration(BaseModel):
    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    contract_version: str = Field(..., min_length=1)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "healthy"}


@app.get("/readyz")
def readyz() -> dict:
    return {"status": "ready"}


@app.post("/v1/bootstrap/register")
def register_product(request: RegisterRequest) -> dict:
    _registered_products[request.product] = request.model_dump()
    return {"status": "registered", "product": request.product}


@app.get("/v1/bootstrap/capabilities")
def list_capabilities(product: str | None = None) -> dict:
    caps = _capabilities
    if product:
        caps = [c for c in caps if c.get("product") == product]
    return {"capabilities": caps}


@app.post("/v1/bootstrap/capabilities")
def add_capability(cap: CapabilityRegistration) -> dict:
    _capabilities.append(cap.model_dump())
    return {"status": "added", "capability": cap.name}


@app.get("/v1/bootstrap/products")
def list_products() -> dict:
    return {"products": list(_registered_products.values())}
