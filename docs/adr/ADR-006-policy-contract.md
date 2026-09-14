# ADR-006: Contract-First RBAC/ABAC Policy Adapter

- Status: Accepted
- Date: 2026-09-14
- Owners: @arca-suite/platform

## Context

Arca Suite products need consistent authorization without embedding OPA, Rego, Cedar, or custom RBAC engines directly. ArcaX and ArcaQ vault may provide their own policy stores, but suite modules must not depend on either product when the feature is disabled.

## Decision

Arca Platform defines a neutral policy contract:

1. `PolicyEvalRequest` captures subject, resource, action and environment attributes.
2. `PolicyEvalResponse` returns `permit`, `deny` or `indeterminate`.
3. `PolicyAdapter` is a protocol that ArcaX, ArcaQ vault, or any IdP can implement.
4. `NullPolicyAdapter` is the safe default (deny-all) when no engine is configured.

Products call `adapter.evaluate(request)` and act on the decision. They do not import ArcaX or ArcaQ vault types.

## Consequences

- ArcaX and ArcaQ vault can plug in without owning suite modules.
- Modules work without ArcaQ and without ArcaX when policy integration is disabled.
- Policy engine changes are isolated behind the adapter.

## Compliance

- No suite module imports ArcaX or ArcaQ vault policy code directly.
- All authorization decisions flow through the `PolicyAdapter` interface.
