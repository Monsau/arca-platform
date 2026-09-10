# ADR-003: Submodules as Product References

- Status: Accepted
- Date: 2026-09-05

## Context

The platform must know which version of each product `-k8s` repository to
deploy. Copying manifests would fork them; remote URLs would not pin versions.

## Decision

Use git submodules under `subprojects/`. Each submodule points to the
`main` branch of a product `-k8s` repository. The platform commit records the
exact submodule SHA, making every deployment reproducible.

## Consequences

- `git clone --recurse-submodules` or `git submodule update --init` is required.
- Updating a product version is an explicit platform commit changing the
  submodule SHA.
- Product teams retain full ownership of their manifests.
