# Platform Shared Resources

This directory contains the shared infrastructure that every Arca Suite
product expects on `server01`:

- Kafka cluster endpoint (`kafka.platform.svc.cluster.local:9092`)
- OpenTelemetry collector endpoint (`otel-collector.platform.svc.cluster.local:4317`)
- Vault / External Secrets Operator backend

These resources are **not** deployed by the product `-k8s` repositories;
they are provisioned once per cluster by the platform team.
