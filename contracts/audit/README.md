# Audit Contract

## Purpose

Define a common, tamper-evident audit record for security-relevant actions
across Arca Suite. Every product emits audit records for actions that change
state, cross a trust boundary or touch governed resources, so that platform
tooling (SOC, Trust, Cert) can reconstruct *who did what, when, and with what
result* — with non-repudiation and traceability (see README §15).

Audit records are distinct from domain events (`contracts/events/`): events
carry business facts, audit records carry accountability facts.

## API surface

- **Emit** — every product MUST emit one audit record per security-relevant
  action, on its own audit sink (append-only). The platform does not define a
  mandatory transport: Kafka topic, audit API or append-only log are all
  valid adapters, but the record format below is mandatory.
- **Fields** — see `schemas/audit/audit-event-schema.json`. Core fields:
  `audit_id` (UUID), `timestamp` (ISO-8601), `actor` (identity of the
  caller, propagated — never re-created — per ADR-006), `action`
  (dotted action name, e.g. `ontology.change_proposed`), `resource`,
  `outcome` (`success|denied|failure`), `correlation_id`, `tenant_id`,
  `entry_point` (provenance of the logical entry point, e.g. `suite` —
  caller-controlled values are forbidden per EP-09), `prev_hash`/`hash`
  (hash-chain linkage for tamper evidence).
- **Integrity** — `hash` is computed over the canonical JSON of the record
  excluding the `hash` field; `prev_hash` links to the previous record of
  the same `chain` so removal or reordering is detectable (EP-03
  falsification-test requirement).

## Example

```json
{
  "audit_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-09-21T10:15:00Z",
  "actor": { "subject": "user-42", "roles": ["admin"] },
  "action": "ontology.change_proposed",
  "resource": { "type": "change_proposal", "id": "cp-7" },
  "outcome": "success",
  "correlation_id": "corr-abc-123",
  "tenant_id": "tenant-1",
  "entry_point": "suite",
  "chain": "arca-hub",
  "prev_hash": "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c",
  "hash": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
}
```

## Status

Implemented schema (`schemas/audit/`). Reference emitters live in product
repositories (embedded SOCs); the transport adapter is deployment-specific.
