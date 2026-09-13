# ADR-001: Arca Platform Bounded Context & Ownership

- Status: Accepted
- Date: 2026-09-13
- Owners: @arca-suite/platform

## Context

Arca Suite contains multiple autonomous products. Without an explicit shared runtime boundary, each product would re-implement common concerns such as configuration, identity, observability and audit.

## Decision

Define Arca Platform as the deployment-neutral shared runtime foundation. Its bounded context includes platform contracts, shared conventions, adapters and bootstrap capabilities. It explicitly excludes business logic, reasoning, execution governance and product-specific data models.

## Consequences

- Products stay focused on their domain.
- Common concerns are defined once and reused.
- Arca Platform does not become a monolith.

## Compliance

- No duplication of ArcaQ or ArcaX responsibilities.
- No business logic in platform code.
