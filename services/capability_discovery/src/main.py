"""Capability Discovery API.

Products query this API to discover platform capabilities and the contracts
required to use them.
"""

from __future__ import annotations

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Arca Capability Discovery API", version="0.1.0")

_capabilities: list[dict] = []


class Capability(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    input_schema: str = Field(..., min_length=1)
    output_schema: str = Field(..., min_length=1)
    required_contracts: list[str] = Field(default_factory=list)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "healthy"}


@app.post("/v1/capabilities")
def register_capability(cap: Capability) -> dict:
    _capabilities.append(cap.model_dump())
    return {"status": "registered", "id": cap.id}


@app.get("/v1/capabilities")
def search_capabilities(
    product: str | None = Query(default=None),
    contract: str | None = Query(default=None),
) -> dict:
    results = _capabilities
    if product:
        results = [c for c in results if c.get("product") == product]
    if contract:
        results = [
            c for c in results if contract in c.get("required_contracts", [])
        ]
    return {"capabilities": results}
