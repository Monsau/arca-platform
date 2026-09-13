# Events Contract

## Purpose

Define a common envelope for cross-product events carried by the platform event backbone.

## Contract

Every platform event MUST include:

- `event_id` — unique event identifier (UUID).
- `event_type` — stable event type name.
- `source` — product that produced the event.
- `timestamp` — ISO-8601 timestamp.
- `correlation_id` — trace correlation identifier.
- `tenant_id` — tenant or workspace identifier.
- `payload` — event-specific payload (JSON).

## Example

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "arca.flow.workflow.completed",
  "source": "arca-flow",
  "timestamp": "2026-09-13T12:00:00Z",
  "correlation_id": "abc-123",
  "tenant_id": "tenant-1",
  "payload": { "workflow_id": "wf-42", "status": "completed" }
}
```

## Status

Planned. Kafka is one possible adapter; other event backbones may be added.
