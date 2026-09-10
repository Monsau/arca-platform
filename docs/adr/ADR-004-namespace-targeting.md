# ADR-004: Namespace Targeting on server01

- Status: Accepted
- Date: 2026-09-05

## Context

The target cluster `server01` uses a single namespace `arcasuite` for the
whole suite. Product `-k8s` bases declare their own namespace for standalone
use.

## Decision

The `clusters/server01/overlays/arcasuite/kustomization.yaml` sets
`namespace: arcasuite`. Kustomize overrides the namespace declared in each
product base. Product names stay unique by their module key prefix.

## Consequences

- One namespace to monitor and secure on server01.
- Products can still be deployed standalone in their own namespace if needed.
- NetworkPolicies must remain permissive enough for cross-product traffic
  within `arcasuite`.
