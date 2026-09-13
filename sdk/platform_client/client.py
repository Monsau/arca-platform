"""Arca Platform client for product-to-platform interactions.

Products use this client to register themselves, discover capabilities and
consume platform services without hard-coding infrastructure addresses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class CapabilityDescriptor:
    name: str
    version: str
    endpoint: str
    contract_version: str


class PlatformClient:
    """Minimal client for platform bootstrap and capability discovery."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=10.0)

    def register(
        self,
        product: str,
        version: str,
        contracts: list[str],
    ) -> dict[str, Any]:
        payload = {
            "product": product,
            "version": version,
            "contracts": contracts,
        }
        response = self._http.post("/v1/bootstrap/register", json=payload)
        response.raise_for_status()
        return response.json()

    def discover_capabilities(self, product: str | None = None) -> list[CapabilityDescriptor]:
        params = {"product": product} if product else None
        response = self._http.get("/v1/bootstrap/capabilities", params=params)
        response.raise_for_status()
        data = response.json()
        return [
            CapabilityDescriptor(
                name=item["name"],
                version=item["version"],
                endpoint=item["endpoint"],
                contract_version=item["contract_version"],
            )
            for item in data.get("capabilities", [])
        ]

    def close(self) -> None:
        self._http.close()
