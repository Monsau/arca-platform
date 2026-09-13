"""Platform Registry API.

Stores platform-level metadata and service descriptors so that products and
adapters can discover each other without hard-coding endpoints.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Arca Platform Registry API", version="0.1.0")

_service_descriptors: dict[str, dict] = {}


class ServiceDescriptor(BaseModel):
    name: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    endpoint: str = Field(..., min_length=1)
    health_endpoint: str = Field(default="/healthz")
    contracts: list[str] = Field(default_factory=list)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "healthy"}


@app.post("/v1/registry/services")
def register_service(descriptor: ServiceDescriptor) -> dict:
    key = f"{descriptor.product}:{descriptor.name}"
    _service_descriptors[key] = descriptor.model_dump()
    return {"status": "registered", "key": key}


@app.get("/v1/registry/services")
def list_services(product: str | None = None) -> dict:
    services = list(_service_descriptors.values())
    if product:
        services = [s for s in services if s.get("product") == product]
    return {"services": services}


@app.get("/v1/registry/services/{product}/{name}")
def get_service(product: str, name: str) -> dict:
    key = f"{product}:{name}"
    if key not in _service_descriptors:
        raise HTTPException(status_code=404, detail="Service not found")
    return _service_descriptors[key]
