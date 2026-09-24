"""Reference discovery adapter for the Arca Platform discovery contract.

Implements the service-descriptor registry surface of
`contracts/discovery/`: register, list (optionally by product) and fetch
one descriptor. Two backends:

- ``InMemoryServiceRegistry`` — default, for tests and local development.
- ``SqlServiceRegistry`` — SQLite/PostgreSQL via ``sdk/common/persistence.py``
  with an idempotent boot migration; the production-facing mode.

The reference services (`services/platform_registry/`,
`services/capability_discovery/`) build on these stores.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

from sqlalchemy import Column, MetaData, String, Table, select

from sdk.common.persistence import PlatformStore

Descriptor = dict


@runtime_checkable
class ServiceRegistry(Protocol):
    """Neutral interface for the service descriptor registry."""

    def register(self, descriptor: Descriptor) -> str:
        ...

    def list(self, product: str | None = None) -> list[Descriptor]:
        ...

    def get(self, product: str, name: str) -> Descriptor | None:
        ...


def descriptor_key(descriptor: Descriptor) -> str:
    return f"{descriptor['product']}:{descriptor['name']}"


class InMemoryServiceRegistry:
    """Default in-memory registry (tests, local development)."""

    def __init__(self) -> None:
        self._descriptors: dict[str, Descriptor] = {}

    def register(self, descriptor: Descriptor) -> str:
        key = descriptor_key(descriptor)
        self._descriptors[key] = dict(descriptor)
        return key

    def list(self, product: str | None = None) -> list[Descriptor]:
        descriptors = list(self._descriptors.values())
        if product:
            descriptors = [d for d in descriptors if d.get("product") == product]
        return descriptors

    def get(self, product: str, name: str) -> Descriptor | None:
        return self._descriptors.get(f"{product}:{name}")


class SqlServiceRegistry:
    """SQL-backed registry with an idempotent boot migration."""

    def __init__(self, store: PlatformStore) -> None:
        self._store = store
        metadata = MetaData()
        self._table = Table(
            "service_registry",
            metadata,
            Column("key", String(256), primary_key=True),
            Column("descriptor_json", String(4096), nullable=False),
        )
        # Idempotent boot migration — safe on every startup.
        self._store.ensure_schema(self._table)

    def register(self, descriptor: Descriptor) -> str:
        key = descriptor_key(descriptor)
        with self._store.session() as s:
            existing = s.execute(
                select(self._table).where(self._table.c.key == key)
            ).first()
            if existing is None:
                s.execute(
                    self._table.insert().values(
                        key=key, descriptor_json=json.dumps(descriptor)
                    )
                )
            else:
                s.execute(
                    self._table.update()
                    .where(self._table.c.key == key)
                    .values(descriptor_json=json.dumps(descriptor))
                )
        return key

    def list(self, product: str | None = None) -> list[Descriptor]:
        with self._store.session() as s:
            rows = s.execute(select(self._table)).all()
        descriptors = [json.loads(r.descriptor_json) for r in rows]
        if product:
            descriptors = [d for d in descriptors if d.get("product") == product]
        return descriptors

    def get(self, product: str, name: str) -> Descriptor | None:
        with self._store.session() as s:
            row = s.execute(
                select(self._table).where(self._table.c.key == f"{product}:{name}")
            ).first()
        return json.loads(row.descriptor_json) if row else None


@runtime_checkable
class CapabilityRegistry(Protocol):
    """Neutral interface for the capability descriptor registry."""

    def register(self, capability: Descriptor) -> str:
        ...

    def search(
        self, product: str | None = None, contract: str | None = None
    ) -> list[Descriptor]:
        ...


class InMemoryCapabilityRegistry:
    """Default in-memory capability registry (tests, local development)."""

    def __init__(self) -> None:
        self._capabilities: list[Descriptor] = []

    def register(self, capability: Descriptor) -> str:
        self._capabilities = [
            c for c in self._capabilities if c.get("id") != capability["id"]
        ]
        self._capabilities.append(dict(capability))
        return capability["id"]

    def search(
        self, product: str | None = None, contract: str | None = None
    ) -> list[Descriptor]:
        results = list(self._capabilities)
        if product:
            results = [c for c in results if c.get("product") == product]
        if contract:
            results = [c for c in results if contract in c.get("required_contracts", [])]
        return results


class SqlCapabilityRegistry:
    """SQL-backed capability registry with an idempotent boot migration."""

    def __init__(self, store: PlatformStore) -> None:
        self._store = store
        metadata = MetaData()
        self._table = Table(
            "capability_registry",
            metadata,
            Column("id", String(128), primary_key=True),
            Column("capability_json", String(4096), nullable=False),
        )
        # Idempotent boot migration — safe on every startup.
        self._store.ensure_schema(self._table)

    def register(self, capability: Descriptor) -> str:
        with self._store.session() as s:
            existing = s.execute(
                select(self._table).where(self._table.c.id == capability["id"])
            ).first()
            if existing is None:
                s.execute(
                    self._table.insert().values(
                        id=capability["id"], capability_json=json.dumps(capability)
                    )
                )
            else:
                s.execute(
                    self._table.update()
                    .where(self._table.c.id == capability["id"])
                    .values(capability_json=json.dumps(capability))
                )
        return capability["id"]

    def search(
        self, product: str | None = None, contract: str | None = None
    ) -> list[Descriptor]:
        with self._store.session() as s:
            rows = s.execute(select(self._table)).all()
        capabilities = [json.loads(r.capability_json) for r in rows]
        if product:
            capabilities = [c for c in capabilities if c.get("product") == product]
        if contract:
            capabilities = [
                c for c in capabilities if contract in c.get("required_contracts", [])
            ]
        return capabilities
