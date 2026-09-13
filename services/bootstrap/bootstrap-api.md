# Platform Bootstrap API

## Purpose

Define a minimal API used by products to register themselves with the platform at startup.

## Operations

- `POST /v1/bootstrap/register` — register product instance, version and supported contracts.
- `GET /v1/bootstrap/capabilities` — discover platform capabilities available to the product.

## Status

Planned. No production code exists yet.
