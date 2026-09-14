# ADR-005: Contract-First Identity and SSO Model

- Status: Accepted
- Date: 2026-09-14
- Owners: @arca-suite/platform

## Context

Arca Suite products need a consistent way to authenticate users and workloads without being locked into a specific IdP. Hard-coding Keycloak, Entra ID, Okta or SPIFFE semantics into product code would create hidden coupling and make multi-environment deployments difficult.

## Decision

Arca Platform defines a deployment-neutral identity contract covering:

1. OIDC discovery via `/.well-known/openid-configuration`.
2. A normalized JWT claims model (`sub`, `iss`, `aud`, `exp`, `iat`, `roles`, `groups`, `scope`).
3. A `WorkloadIdentity` abstraction for service accounts and machine identities.

Products consume `IdentityToken` and `WorkloadIdentity` objects produced by adapters. Adapters map concrete IdPs to the contract. No product implements provider-specific logic.

## Consequences

- Products remain IdP-agnostic.
- New IdPs only require a new adapter.
- Identity data is versioned and auditable through the contract.

## Compliance

- No product imports Keycloak, Entra ID, Okta or SPIFFE libraries directly.
- All identity data consumed by products comes through the contract types.
