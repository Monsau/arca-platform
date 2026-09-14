# ArcaQ Linkage Audit — Arca Suite V2.3

**Date:** 2026-09-14  
**Scope:** Cross-module functional linkages between `arcaq` and the standardized Arca Suite products (Flow, Decision Room, Hub, Exchange, Packs, Trust, Studio, Bench, Cert).  
**Constraint:** All linkages must remain optional so the suite can still operate without ArcaQ or ArcaX.

## 1. Current state

### 1.1 ArcaQ capabilities relevant to the suite

`arcaq` is a multi-module knowledge & decision platform. Capabilities used by Arca Suite are:

| Capability | ArcaQ module | Integration surface |
|---|---|---|
| Knowledge Graph / Jena | `arcaq-brain` | REST `/api/v1/knowledge`, `/api/v1/search`, SPARQL |
| Decision Intelligence | `arcaq-api` | REST `/api/v1/decisions/*` |
| Causal reasoning | `arcaq-causal` | REST `/api/v1/causal/*` |
| OOC / Ontology contracts | `arcaq-api` | REST `/api/v1/ooc/*`, `/api/v1/ontology-olm/*` |
| Ontology lifecycle | `arcaq-ontology-builder` | Agent event bus + Kafka `arcaq.enrichment.events` |
| SOC events | `arcaq-soc-*` | Kafka `arcaq.soc.events`, `arcaq.soc.alerts`, `arcaq.soc.verdicts` |
| Platform events | `arcaq-api` | Kafka `arcaq.platform.events` |
| Connectors / MCP | `arcaq-connect` | MCP JSON-RPC on `:8005` |

### 1.2 Existing suite linkages

No standardized Arca Suite module currently imports `arcaq` code or calls ArcaQ APIs. The only implemented cross-module event flows are:

```text
Decision Room ──decision-room.decision.sealed──► Flow
                                              └─► Hub

Bench ──bench.results──► Cert
                     └─► Trust
                     └─► Hub

Cert ──cert.package.created──► Trust
    ──asset.published───────► Exchange

Exchange ──asset.published──► Packs
         ──asset.published──► Studio
         ──asset.published──► Trust
```

### 1.3 ArcaQ-specific gaps

| Consumer module | Expected ArcaQ linkage | Current status |
|---|---|---|
| `arca-decision-room` | Enrich decision packages with ArcaQ KG context, ontology-grounded evidence, SME corrections | **Missing** — decisions are sealed from human votes only |
| `arca-flow` | Fetch ArcaQ context/recommendations for workflow steps; validate actions against OOC | **Missing** — only reacts to sealed decisions |
| `arca-hub` | Display ArcaQ knowledge events, causal insights, decision intelligence, ontology updates | **Missing** — cockpit aggregates only suite events |
| `arca-exchange` | Ingest ontologies, OOC contracts, and certified assets from ArcaQ marketplace | **Missing** — registry is isolated |
| `arca-packs` | Import ArcaQ KG / ontology artifacts into pack `ontology/` directories | **Missing** |
| `arca-studio` | Hydrate Ontology Mapper from ArcaQ/Exchange ontology assets | **Missing** — catalog is pluggable but empty |
| `arca-trust` | Ingest ArcaQ provenance, ReBAC decisions, KG-derived risk signals | **Missing** |
| `arca-bench` | Run KG-grounded benchmarks; evaluate decision-package quality | **Missing** |
| `arca-cert` | Include ArcaQ compliance/ontology evidence in certification packages | **Missing** |

## 2. Recommended contract-first linkages

All linkages should be implemented as **optional contracts** (REST/GraphQL, Kafka, MCP, OOC). No module may depend on ArcaQ at compile/runtime when disabled.

### 2.1 Kafka topics to consume from ArcaQ

| Topic | ArcaQ owner | Suite consumers | Purpose |
|---|---|---|---|
| `arcaq.platform.events` | `arcaq-api` | Hub, Trust | Platform lifecycle, audit, tenant-scoped notices |
| `arcaq.enrichment.events` | `arcaq-brain` / `arcaq-ontology-builder` | Hub, Exchange, Studio, Packs | KG enrichment, ontology updates, new OOC versions |
| `arcaq.soc.verdicts` | `arcaq-soc-analyzer` | Trust, Hub | Risk verdicts that affect trust posture |
| `arcaq.prov-o.traces` | `arcaq-causal` / decisions | Trust, Cert | Immutable provenance for evidence bundles |

### 2.2 REST/GraphQL contracts

| ArcaQ endpoint | Suite consumer | Use case |
|---|---|---|
| `GET /api/v1/decisions/{id}` | Decision Room, Flow | Fetch decision context, options, justification |
| `GET /api/v1/knowledge/{entity}` | Decision Room, Flow, Hub | Resolve KG entities referenced by decisions |
| `GET /api/v1/ooc/contracts/{id}` | Exchange, Studio, Packs | Fetch published OOC contracts |
| `GET /api/v1/search` | Hub | Semantic search across the KG |
| `GET /api/v1/causal/prov-trace` | Trust, Cert | Fetch PROV-O trace for evidence |

### 2.3 MCP capabilities

| Capability | Provider | Consumer | Purpose |
|---|---|---|---|
| `knowledge_graph_query` | `arcaq-connect` | Flow, Decision Room, Hub | SPARQL-like KG lookup |
| `ooc_validate` | `arcaq-connect` | Studio, Exchange, Packs | Validate OOC contract against ArcaQ |
| `decision_context` | `arcaq-connect` | Decision Room | Fetch decision context for a question |

## 3. Implementation priorities

1. **P0 — Hub consumer for `arcaq.platform.events` and `arcaq.enrichment.events`**
   - Adds cockpit visibility into ArcaQ without changing ArcaQ code.
   - Gracefully degrades when ArcaQ is not deployed.
   - Reuses the same opt-in Kafka consumer pattern already used by Trust and Studio.

2. **P1 — Decision Room ↔ ArcaQ context bridge**
   - Optional REST client to `/api/v1/decisions` and `/api/v1/knowledge`.
   - Enriches the Decision Package with KG context before sealing.

3. **P1 — Exchange ontology ingestion from ArcaQ**
   - Optional sync job consuming `arcaq.enrichment.events` and registering ontologies/OOCs.

4. **P2 — Studio ontology mapper catalog feed**
   - Populate the mapper from Exchange ontology assets (already partially linked via `asset.published`) and optionally from ArcaQ OLM.

5. **P2 — Trust ArcaQ provenance ingestion**
   - Consume `arcaq.prov-o.traces` and `arcaq.soc.verdicts` to augment posture scores.

## 4. Guardrails

- All ArcaQ linkages must be **opt-in** via feature flags (`HUB_KAFKA_CONSUME_ARCAQ`, `DECISION_ROOM_ARCAQ_CONTEXT_URL`, etc.).
- No Arca Suite module may require ArcaQ to start or pass tests.
- No direct database access to ArcaQ.
- All interactions through versioned contracts (Kafka Avro, OpenAPI, GraphQL SDL, MCP JSON Schema).
- When ArcaQ is absent, the module must behave exactly as before.
