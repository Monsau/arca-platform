# Lifecycle Contract

## Purpose

Define a common service lifecycle vocabulary so that platform tooling
(bootstrap, orchestrators, k8s operators in `arca-platform-k8s`) can drive
and observe every product the same way, whatever the deployment technology.

The lifecycle adapter maps product-local states onto this contract;
`services/bootstrap/` is the reference consumer.

## API surface

- **States** — see `schemas/lifecycle/lifecycle-state-schema.json`:
  `registered` → `starting` → `ready` (or `degraded`) → `stopping` →
  `stopped`. `failed` is reachable from any non-terminal state.
- **Transitions** — `registered→starting`, `starting→ready|degraded|failed`,
  `ready→degraded`, `degraded→ready|failed`, `ready|degraded|failed→stopping`,
  `stopping→stopped`.
- **Transition events** — every transition MUST be recorded as a
  `LifecycleTransitionEvent`
  (`schemas/lifecycle/lifecycle-transition-schema.json`) with `timestamp`,
  `product`, `instance_id`, `from_state`, `to_state`, `reason` and
  `correlation_id`. Transition events are audit-relevant: consumers SHOULD
  also emit an audit record per `contracts/audit/`.
- **Probes** — liveness/readiness are reported through the health contract
  (`contracts/health/`), not duplicated here.

## Status

Implemented schema; reference in-memory/SQL-backed adapter in
`adapters/lifecycle/`.
