# ADR-004: Platform Contract Versioning & Compatibility

- Status: Accepted
- Date: 2026-09-13
- Owners: @arca-suite/platform

## Context

As Arca Suite evolves, platform contracts will change. Products must be able to declare which contract versions they support and upgrade independently.

## Decision

Platform contracts follow semantic versioning. Breaking changes require a major version bump and an ADR. Products declare supported contract versions in their service descriptors. Compatibility matrices are maintained in `docs/integration/`.

## Consequences

- Products can upgrade at different speeds.
- Breaking changes are explicit and documented.
- Compatibility testing is required for each contract version.

## Compliance

- No breaking change without ADR and major version bump.
- Compatibility matrices are kept up to date.
