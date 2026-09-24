# Configuration Contract

## Purpose

Define how platform configuration documents are structured and loaded so that
every product reads configuration the same way: environment variables first,
configuration file second, secret references never inline (see
`contracts/secrets/`).

The reference loading conventions live in `sdk/common/config.py`
(`PlatformSettings`, `load_from_file`); this contract pins the document
shape those conventions consume.

## API surface

- **Load** — the file document is consumed by
  `adapters/configuration/configuration_adapter.py` (`FileConfigurationAdapter`,
  YAML or JSON, dotted-key `get()`). `PlatformSettings.load_from_file` in
  `sdk/common/config.py` reads the flat keys (`environment`, `tenant_id`,
  `log_level`, `*_adapter`) and ignores unknown keys; the `ARCA_*`
  environment-first convention is the suite-wide rule.
- **Adapter selection** — the `adapters.*` keys carry the adapter name per
  capability domain (identity, secrets, messaging, observability,
  ontology-write). Values are adapter names, never classes or connection
  strings with credentials. Wiring these keys into runtime adapter
  selection is **planned**; today the file adapter only exposes them via
  `get("adapters.<domain>")`.
- **Secret references** — any field that needs a secret carries a reference
  (`{ "secret_ref": "vault:secret/data/x#key" }`) instead of a value.

## Document shape (summary)

Top-level keys: `environment`, `tenant_id`, `log_level`, `adapters`
(identity / secrets / messaging / observability / ontology_write),
`endpoints` (registry, discovery, bootstrap — plain `host:port` or URLs,
no credentials), `messaging` (bootstrap_servers, topic_prefix, consumer_group),
`observability` (otel_endpoint, metrics_enabled).

## Status

Implemented schema and SDK loader (`sdk/common/config.py`); file-backed
adapter in `adapters/configuration/`.
