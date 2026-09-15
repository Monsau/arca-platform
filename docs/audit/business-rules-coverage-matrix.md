# Arca Suite V2.3 — Business Rules Coverage Matrix

**Scope:** core products (`arca-decision-room`, `arca-flow`, `arca-hub`, `arca-exchange`, `arca-trust`, `arca-cert`, `arca-packs`, `arca-studio`).  
**Method:** code-level audit of `src/core/domain`, `src/core/services`, `src/policies`, `contracts`, `docs/adr` and tests.  
**Date:** 2026-09-14  
**Status legend:**

- ✅ Implemented — executable rule with tests
- ⚠️ Partial — stub, placeholder, or partially wired
- ❌ Missing — documented/expected but not implemented
- ➖ Not applicable

---

## Cross-cutting governance rules

| Rule | Decision Room | Flow | Hub | Exchange | Trust | Cert | Packs | Studio |
|---|---|---|---|---|---|---|---|---|
| RBAC scope/role enforcement | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ABAC attribute checks | ⚠️ (helpers only) | ⚠️ (resource ignored) | ⚠️ (helpers only) | ⚠️ (Python mirror only) | ⚠️ (basic ownership) | ✅ | ⚠️ (not enforced) | ⚠️ (not enforced) |
| OPA/Rego runtime evaluation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Rate limiting / DoS protection | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Request idempotency | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Audit / immutable ledger | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) | ⚠️ (in-memory SOC) |
| Evidence signing / hash chain | ❌ | ❌ | ❌ | ❌ | ✅ (report seal) | ✅ (dossier seal) | ❌ | ❌ |
| Vault signing/encryption | ✅ (Transit signer) | ✅ (Transit field encryption) | ❌ | ❌ | ❌ | ❌ | ⚠️ (ref only) | ❌ |
| OpenTelemetry instrumentation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Contract conformance tests | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Versioned DB migrations | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Product-specific rules

### Arca Decision Room

| Rule | Status | Notes |
|---|---|---|
| Quorum & weighted voting | ✅ | `entities.py`, `aggregates.py` |
| Separation of duties (proposer/voter/sealer) | ✅ | Domain + ABAC + Rego |
| Override justification | ✅ | Non-empty justification enforced |
| Sealing immutability | ✅ | Frozen package + sealed-row guard |
| Review verdict gate | ✅ | `UNFAVORABLE` review blocks sealing unless override recorded |
| Vault-backed signing / sealing | ✅ | `VaultTransitSigner`; dev signer blocked in production |
| Workspace role enforcement | ❌ | Roles stored but not interpreted |
| Vote signature verification | ❌ | Field exists, never verified |
| Field-level encryption | ✅ | Override justifications, rationale and scenario notes encrypted at rest; Vault Transit in production, Fernet dev fallback blocked in production |
| Retention enforcement | ❌ | Documented only |

### Arca Flow

| Rule | Status | Notes |
|---|---|---|
| Workflow state machine | ✅ | `models.py`, `engine.py` |
| HITL approval gate | ✅ | `engine.py` |
| Compensation (status) | ✅ | Marks instances/steps cancelled |
| Evidence binding | ✅ | Per-transition evidence rows |
| Transactional SQL outbox + Kafka drain | ✅ | `OutboxEventRow` persisted with instance, `OutboxDrainer` flush |
| OOC contract gate | ✅ | Feature-flagged HTTP client |
| Step retry policy | ✅ | `max_retries` enforced before compensation; `flow.step.retrying` emitted |
| Step timeout | ✅ | Per-step `timeout_seconds` + `TimeoutWatchdog` + `flow.step.timeout` |
| Real compensation actions | ✅ | `CompensationExecutor` invoked per compensated step; evidence + event emitted |
| SLA/approval-deadline watchdog | ✅ | Per-step `approval_timeout_seconds` + `ApprovalDeadlineWatchdog` |
| Field-level encryption | ✅ | Sensitive evidence (`kind == 'sensitive'`) encrypted at rest; Vault Transit in production, Fernet dev fallback blocked in production |
| Multi-party approval quorum | ❌ | One approval per step |
| Workflow definition immutability | ❌ | No deprecation/upgrade policy |

### Arca Hub

| Rule | Status | Notes |
|---|---|---|
| RBAC scope-per-view | ✅ | 8 views × 8 scopes |
| JWT/OIDC validation | ✅ | JWKS + dev bypass |
| Timeline / lineage builder | ✅ | Event-driven graph |
| Trust/risk/cost scoring | ✅ | `trust.py`, `overview.py` |
| OpenMetadata lineage export | ⚠️ | Flag respected; HTTP push stubbed |
| Persistent SQL store | ✅ | `Store` + `HubRepository` with QueryEvent/ViewCache tables |
| Rate limiting | ❌ | No middleware |
| Upstream resilience (CB/retry) | ✅ | `CircuitBreaker` + retries with exponential backoff in `HttpUpstreamClient` |
| Approval write-through to ArcaFlow | ❌ | Local record only |
| Cache invalidation on events | ❌ | TTL only |

### Arca Exchange

| Rule | Status | Notes |
|---|---|---|
| SemVer validation | ✅ | `domain/__init__.py` |
| Dependency DAG + cycle detection | ✅ | `domain/__init__.py` |
| Trust-level publication gate | ✅ | `validated`/`certified` only |
| Certification separation of duties | ✅ | `certification.py` |
| Federation peer whitelist | ⚠️ | No actual HTTP sync |
| Asset signing verification | ❌ | Vault stubs |
| Validation pipeline | ❌ | Trust set on submit |
| Rate/quotas | ❌ | Documented only |

### Arca Trust

| Rule | Status | Notes |
|---|---|---|
| Score dimensions & clamping | ✅ | `scores.py` |
| Report seal & validity | ✅ | SHA-256 + 90-day window |
| Compliance scoring | ✅ | `compliance_service.py` |
| Risk scoring | ✅ | Diminishing returns formula |
| Kafka outbox flush | ✅ | Transactional SQL outbox + `OutboxDrainer` to Kafka |
| Score staleness alerting | ❌ | Not implemented |
| Retention enforcement | ❌ | Documented only |
| mTLS/SPIFFE | ❌ | Not implemented |

### Arca Cert

| Rule | Status | Notes |
|---|---|---|
| Dossier lifecycle | ✅ | `cert_models.py` |
| Seal & tamper detection | ✅ | `verify_seal()` |
| Readiness scoring | ✅ | Threshold 0.7 default |
| Remediation planning | ✅ | Per-dimension actions |
| OOC governance gate before publish | ✅ | `HttpOOCGateClient`; blocks `publish_dossier` when not approved |
| Multi-reviewer approval | ❌ | Single reviewer |
| Immutable audit log | ❌ | In-memory SOC |
| GraphQL RBAC | ❌ | No permission checks |

### Arca Packs

| Rule | Status | Notes |
|---|---|---|
| Pack lifecycle state machine | ✅ | `pack.py` |
| Manifest schema validation | ✅ | `manifest.py` |
| SemVer / suite compatibility | ✅ | `version.py`, `compatibility.py` |
| SoD on deprecation | ✅ | Approver ≠ publisher |
| Signature reference check | ⚠️ | Reference only, no crypto |
| OOC schema validation | ❌ | `save_manifest/get_manifest` stubs |
| Conformance test execution | ❌ | Metadata checks only |
| GraphQL authorization | ❌ | Mutations bypass RBAC/ABAC |

### Arca Studio

| Rule | Status | Notes |
|---|---|---|
| Project lifecycle | ✅ | `project.py` |
| OOC artifact required for validation | ✅ | `project.py` |
| Published immutability | ✅ | `project.py` |
| Content addressing | ✅ | SHA-256 digests |
| Policy simulation | ✅ | `policy.py` |
| ABAC enforcement | ❌ | Helpers not wired |
| GraphQL authorization | ❌ | Only reader gate |
| Real OOC schema validation | ❌ | Top-key check only |
| Asset trust-level gating | ❌ | Stored but unused |

---

## Prioritized gap backlog

### P0 — Must implement before any production exit gate

1. **Review-verdict gate in Decision Room** — `UNFAVORABLE` expert review must block sealing unless an override is recorded.
2. **Step retry policy in Arca Flow** — `StepExecution.attempt` must be used; per-step `max_retries` must be enforced before compensation.
3. **Rate limiting in Arca Hub** — ADR-002 mandates `429` + `Retry-After` for cockpit endpoints.
4. **Vault signing/encryption** — ✅ Decision Room uses `VaultTransitSigner`; remaining products still use dev signers or plaintext fields.
5. **Kafka outbox flush in Arca Trust** — ✅ implemented and tested.
6. **OOC governance gate in Arca Cert** — ✅ implemented and tested.

### P1 — Should implement for sovereignty / resilience

7. ✅ Field-level encryption for justifications / sensitive evidence.

### P2 — Could have / industrialization

13. OPA runtime enforcement.
14. KEDA autoscaling manifests.
15. Advanced lineage queries / GraphQL federation.
16. Multi-jurisdiction retention policies.

---

## Recommended next actions

Shipped in the latest iterations:

1. ✅ **Decision Room:** Vault-backed signing with production dev-signer blocking.
2. ✅ **Arca Flow:** transactional SQL outbox with Kafka drain.
3. ✅ **Arca Cert:** OOC governance gate before dossier publication.
4. ✅ **Arca Trust:** durable Kafka outbox flush.
5. ✅ **Arca Flow:** step timeout enforcement and real compensation handlers.
6. ✅ **Cross-product:** contract conformance tests and versioned database migrations.
7. ✅ **Decision Room / Arca Flow:** field-level encryption for justifications, rationale, scenario notes and sensitive evidence.

Remaining P1 priorities to address next:

- **Arca Flow:** SLA/approval-deadline watchdog.
- **Arca Hub:** persistent SQL store + migrations and upstream resilience (circuit breaker / retry).
- **Cross-product:** field-level encryption for justifications and sensitive evidence.
