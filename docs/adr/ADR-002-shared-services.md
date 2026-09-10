# ADR-002: Shared Platform Services

- Status: Proposed
- Date: 2026-09-05

## Context

Every product needs Kafka, OpenTelemetry and Vault. These should not be
re-installed by each product.

## Decision

The platform provisions shared services once per cluster in the `arcasuite`
namespace. Product ConfigMaps reference them by stable DNS names. The
ClusterSecretStore for Vault is declared by the platform and consumed by each
product's ExternalSecrets.

## Consequences

- Consistent observability, messaging and secret management.
- Product `-k8s` repositories stay focused on the product workload.
- Shared service upgrades must be coordinated by the platform team.
