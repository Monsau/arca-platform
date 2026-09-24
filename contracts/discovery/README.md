# Discovery Contract

## Purpose

Define how products and capabilities are described and discovered without
hard-coded endpoints. Two descriptor kinds exist:

- **Service descriptors** — what a product exposes (registry).
- **Capability descriptors** — what a product can do for others (capability
  discovery).

The reference services are `services/platform_registry/` and
`services/capability_discovery/`; the reference client is
`sdk/platform_client/client.py`.

## API surface

Service registry:

- `POST /v1/registry/services` — register/update a service descriptor.
- `GET /v1/registry/services?product=` — list descriptors, optionally filtered.
- `GET /v1/registry/services/{product}/{name}` — fetch one descriptor (404 otherwise).

Capability discovery:

- `POST /v1/capabilities` — register a capability descriptor.
- `GET /v1/capabilities?product=&contract=` — search by product and/or
  required contract.

Descriptor shapes are defined by `schemas/discovery/service-descriptor-schema.json`
and `schemas/discovery/capability-descriptor-schema.json`; they mirror the
pydantic models in the reference services and are the single schema source
per EP-06.

## Status

Implemented services (in-memory mode by default, SQL-backed persistence
available via `ARCA_REGISTRY_BACKEND=sql`) and schemas.
