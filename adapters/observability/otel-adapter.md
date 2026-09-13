# OpenTelemetry Adapter

## Purpose

Reference adapter that implements the Arca Platform observability contract using OpenTelemetry.

## Responsibilities

- Collect traces, metrics and logs from product processes.
- Export telemetry to a configured OTLP endpoint.
- Attach standard resource attributes (service.name, service.version, tenant_id).

## Configuration

```yaml
observability:
  adapter: opentelemetry
  otlp:
    endpoint: http://otel-collector:4317
    insecure: true
```

## Status

Planned. `arca-platform-k8s` deploys an OpenTelemetry collector as the Kubernetes implementation.
