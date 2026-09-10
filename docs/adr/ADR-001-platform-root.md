# ADR-001: Platform Root & Namespace Consolidation

- Status: Accepted
- Date: 2026-09-05
- Owners: @arca-suite/platform

## Context

Deploying nine product modules each in its own namespace creates operational
complexity on `server01`. The platform team needs a single root of trust and a
single command to deploy the whole suite.

## Decision

Create `arca-platform` as the platform orchestration root. It:

- Declares the shared `arcasuite` namespace on `server01`.
- References every product `-k8s` repository as a git submodule so versions are
  pinned and auditable.
- Provides a Kustomize overlay that deploys all products into the `arcasuite`
  namespace without modifying the product-owned manifests.

## Consequences

- Products stay autonomous: no product manifest is edited by the platform repo.
- The platform repo is the single source of truth for "what runs where".
- Submodules must be updated explicitly when a product releases a new version.

## Compliance

- No secret in clear text.
- Product isolation is preserved (own SAs, RBAC, NetworkPolicies, mTLS).
