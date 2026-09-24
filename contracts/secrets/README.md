# Secrets Contract

## Purpose

Define how secrets are *referenced* across Arca Suite. Contracts and
configuration reference secrets by name; values never appear in this
repository, in configuration documents or in transit through platform
adapters (README §15).

The reference adapter is `adapters/secrets/vault_adapter.py` (HashiCorp
Vault); the SDK entry point is `sdk/common/config.py::get_secret`.

## API surface

- **Reference format** — `{ "provider": "vault", "path": "secret/data/x",
  "key": "api-token", "version": 3 }`, defined by
  `schemas/secrets/secret-reference-schema.json`. The shorthand string form
  `vault:secret/data/x#api-token` is the conventional spelling in
  configuration documents; a loader that parses and normalises the shorthand
  to the object form is **planned** (no code does this yet — today the object
  form is only validated by the schema).
- **Resolve** — `get_secret(key, default)` in the SDK delegates to the
  configured secrets adapter at runtime. Products call this contract point
  without knowing whether Vault, ESO or another backend is in use.
- **Guarantees** — adapters MUST NOT log resolved values, MUST NOT persist
  them outside the provider, and MUST fail closed (raise / return no value)
  when the provider is unreachable.

## Status

Implemented reference adapter (Vault) and schema; environment-variable
fallback exists for local development and tests only.
