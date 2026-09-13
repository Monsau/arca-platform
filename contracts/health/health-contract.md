# Health Contract

## Purpose

Define a common health, readiness and liveness interface for all Arca Suite products so that platform tooling can discover service health consistently.

## Contract

Every product MUST expose:

- `GET /healthz` — liveness probe. Returns HTTP 200 when the process is alive.
- `GET /readyz` — readiness probe. Returns HTTP 200 when the product can accept traffic.
- `GET /health` — detailed health report (optional). Returns a JSON document with component statuses.

## Response format

```json
{
  "status": "healthy|degraded|unhealthy",
  "version": "1.2.3",
  "checks": {
    "database": { "status": "healthy" },
    "event_backbone": { "status": "healthy" }
  }
}
```

## Status

Planned. Reference implementations live in product repositories.
