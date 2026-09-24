# Observability Contract

## Purpose

Define the telemetry records every product emits so that logs, metrics and
traces from the whole suite are correlatable in one observability backend
(the external observability cluster). Technology (OpenTelemetry, Prometheus)
is an adapter choice, not the contract (README §9).

The reference adapter is `adapters/observability/opentelemetry_adapter.py`.

## API surface

- **Telemetry record** — one envelope per emission, defined by
  `schemas/observability/telemetry-record-schema.json`: `timestamp`,
  `severity` (`debug|info|warning|error`), `product`, `service`,
  `instance_id`, `correlation_id` (propagated from the incoming request or
  message envelope), `trace_id`, `kind` (`log|metric|trace`), `name`
  (metric name / log message / span name) and `attributes` (flat string
  map). Metric records SHOULD use the `arca_*` name prefix reserved by the
  suite observability baseline.
- **Correlation** — `correlation_id` and `trace_id` are mandatory on every
  record so a platform query can join an API call, its events and its audit
  records.
- **Emission** — products emit through the configured observability adapter.
  When no backend is configured, products are expected to skip initialisation
  and emit nothing (local development and tests); a self-degrading no-op
  adapter is **planned** — the current adapter raises if the OpenTelemetry
  packages are missing.

## Status

Reference adapter (`adapters/observability/opentelemetry_adapter.py`)
implements OTLP trace export (`initialize` / `start_span`);
`collect_metric` is a stub. The telemetry record envelope above is
contract-defined; **no code emits it yet** — adapters and products emitting
records in this shape are the next implementation step.
