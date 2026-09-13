# ADR-003: Adapter Model for Infrastructure Implementations

- Status: Accepted
- Date: 2026-09-13
- Owners: @arca-suite/platform

## Context

Arca Suite must run on different infrastructure stacks. Hard-coding Kafka, Kubernetes, Vault or OpenTelemetry into platform contracts would make the platform non-portable.

## Decision

Arca Platform defines deployment-neutral contracts. Each contract is implemented by one or more adapters. Adapters map contracts to concrete technologies. Products consume contracts, not adapters directly.

## Consequences

- The platform is infrastructure-neutral.
- New environments only need new adapters.
- Adapter quality and conformance must be tested.

## Compliance

- No Kubernetes-specific concept in platform contracts.
- Adapters are swappable without changing product business logic.
