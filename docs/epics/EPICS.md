# Arca Suite — Epics

> Governance: this document is the single source of truth for Suite epics
> (`arca-*`). Any change goes through a PR on `arca-platform`.
> Last updated: 2026-09-21 — EP-09 ontology write centralization (multi-entry-point constraint)

## Golden rule — never break ArcaQ or ArcaX

The Suite composes **around** the two products; it does not modify them.
Binding consequences, already validated in `docs/integration/arcaq-linkage-audit.md`:

1. **No compile-time or runtime dependency** on `arcaq` or `arcax` — integration through versioned contracts from this repo (`contracts/`) only.
2. **Single integration pattern**: `Protocol` + `Null` implementation (disabled by default) + `Http` implementation opt-in via feature flag, short timeout, graceful degradation — never a business-flow blockage when a product is down.
3. **Ontologies: reference, never redefine** — a single namespace `http://arcaq.com/ontology#`; core instances (`Jurisdiction_MA`, `Jurisdiction_FR`, `Regulation_Loi0908_MA`, GDPR...) are referenced, never redeclared; no per-territory namespace.
4. **A product does not depend on the Suite to exist** — ArcaQ and ArcaX remain standalone and sellable alone; the Suite adds composition value.
5. **A complete fix = double-loop** — any rule revision ships in the same change: model + contract (SHACL/OpenAPI) + data + the gate that enforces them. A revision that lives in a document while systems keep applying the old rule is not a fix.

---

## Overview

| Epic | Title | Priority | Status |
|---|---|---|---|
| EP-01 | ArcaQ event integration (Kafka backbone) | P0 | In progress (~80%) |
| EP-02 | Decision bridges (KG context, OOC gate) | P0 | Done |
| EP-03 | Uncorruptible trust chain (external bench) | P0 | Planned |
| EP-04 | Pack semantic conformance (RDF/SHACL) | P0 | Done |
| EP-05 | France Sovereignty Pack | P1 | Planned |
| EP-06 | Transverse schema unification (SOC, topics, shared-kernel, OLM/OOC, provenance) | P1 | Planned |
| EP-07 | ArcaQ semantic search in the cockpit | P1 | Planned |
| EP-08 | Claimed metrics under reproducible methodology | P2 | Planned |
| EP-09 | Ontology write centralization (Suite → ArcaQ change proposals) | P0 | In progress (adapter + contract merged in arca-platform; adoptions merged: arca-hub cockpit, arca-packs install, arca-flow definitions) |

---

## EP-01 — ArcaQ event integration

**Status: in progress.** Consume `arcaq.*` topics without ever writing into ArcaQ.

- Done: `arca-hub` (cockpit timeline, opt-in consumer `kafka_arcaq_enabled`), `arca-exchange` (`ArcaqEnrichmentConsumer` → ontology/OOC registries), `arca-flow` OOC gate, `arca-decision-room` (`ArcaqContextClient` Protocol Null/Http).
- Partial: `arca-trust` (PROV-O provenance consumed; **remaining: `arcaq.soc.verdicts` → posture scores**), `arca-cert` (ArcaQ evidence in certification dossiers), `arca-studio` (hydratable catalogue).
- Acceptance criteria: every opt-in consumer has a Null test (disabled = no call) and an Http test (contract payload validated); no consumer blocks the business flow when ArcaQ is unavailable.

## EP-02 — Decision bridges

**Status: done.** KG context embedded in Decision Packages before sealing (decision-room), workflow step validation against `/api/v1/ooc` (flow). One documented gap remains in EP-07.

## EP-03 — Uncorruptible trust chain (external bench)

**Status: planned.** Born from the reward-hacking analysis (2026-09-20).

Problem: the Suite internalized a scoring loop — modules emit their own audit events → Trust computes 6 scores → Cert assembles dossiers → Bench re-scores → remediation flows back to modules. Hacking surfaces: **score inflation** (the scored controls the source of its metric), **unguarded guardian** (Trust/Bench are audited by no one), **confirmation loop** (Cert ← Trust ← Bench cite each other).

Deliverables:
1. `arca-bench` replays **sealed decisions** and verifies the quorum **independently** of emitted events (reconstruction from sealed artifacts, not from the stream).
2. At least one business event is cross-checked against external evidence before it feeds a Trust score.
3. The only score that matters is one a module cannot award itself.
4. **"AI removes the pause" criterion**: every auto-triggered action embeds the concepts, sources and rules it used (not just an event trace) — a fluent explanation proves nothing about what was actually used.

Acceptance criteria: artificially removing one upstream audit event makes the bench fail (falsification test).

## EP-04 — Pack semantic conformance

**Status: done** (arca-packs PR #3, merged 2026-09-20).

MA-CONF-002/003 are assertions over a parsed rdflib graph (triples + language-tagged literals), plus MA-CONF-008 (pack-local SHACL contracts) and MA-CONF-009 (loading the pack into the shared arcaq graph introduces **no new** SHACL violation). String matching was a Goodhart target — semantic validation immediately detected: `LegalDomain` class missing from the core, missing `belongsToDomain` anchors, object usage of `legalBasis` (a DatatypeProperty) on an individual.

Rule now binding for any future pack: **conformance = RDF+SHACL**; textual checks are secondary guards only.

## EP-05 — France Sovereignty Pack

**Status: planned.** Template: `src/packs/morocco-sovereignty/` (merged, aligned on the `arcaq:` namespace).

- Reference `arcaq:Jurisdiction_FR` + GDPR (`arcaq:Regulation_GDPR`) — do not redefine.
- Labels en/fr (Arabic trilingual is Morocco-specific).
- Conformance from the first PR: real RDF/SHACL validation (MA-CONF-008/009 as Definition-of-Done requirements).
- Reuse the pack-level `arcaq:LegalDomain` declaration (introduced by the Morocco pack) or the core class if ArcaQ promotes it (see F-AQ-08 in the flaw register).

## EP-06 — Transverse schema unification

**Status: planned.** Three ecosystems implement the same bricks with different formats (audit finding): SOC 5 pods, Kafka topic registry, shared-kernel, OLM/OOC, PROV-O provenance.

Deliverables:
1. `arca-platform/contracts` becomes the **single schema repository on the Suite side** (its declared role); module-embedded SOCs only emit in the shared-kernel format.
2. Adopt the ArcaX public-import rule: only versioned public packages/contracts are importable, never an internal submodule.
3. **Bounded-context principle**: unification does not create a single universal schema — it builds *explicit translation contracts* between contexts (business contexts keep their distinctions; translation is deliberate, not accidental). A shared identification namespace ≠ one forced definition.
4. Document the boundary: Suite side → `arca-platform` is the source of truth; product side → ArcaQ (`arcaq-kafka-topics`) and ArcaX remain autonomous (golden rule #4). The Suite does not unify the products with each other; it unifies itself.

## EP-07 — ArcaQ semantic search in the cockpit

**Status: planned.** Expose the ArcaQ `GET /api/v1/search` surface in `arca-hub` (cockpit), same Protocol/Null/Http pattern, opt-in. Gap from the integration audit (2026-09-14).

## EP-08 — Claimed metrics under reproducible methodology

**Status: planned.** Every displayed metric (dashboards, README, badges) must point to: methodology + datasets + reproducible result, or be reworded as an unquantified claim. Applies internally (Suite) and as an external recommendation (product badges — see flaw register F-AQ-07).

## EP-09 — Ontology write centralization (Suite → ArcaQ change proposals)

**Status: in progress** (adapter, contract and schemas merged in arca-platform; three module adoptions merged: arca-hub, arca-packs, arca-flow).

Born from the multi-entry-point architecture constraint (2026-09-20): the ontology will be fed centrally through the Suite **in addition to** direct ArcaQ usage. There will be several logical entry points for the same actions, under **identical permission management propagated across the Suite**.

Binding rules (extend golden rule #3 "reference, never redefine" to writes):

1. **ArcaQ remains the single physical writer** (Jena/Fuseki). Suite modules are *clients* of `POST /api/v1/ontology-ops/change-proposals` — never a second writer, so a single chain of custody is preserved.
2. **Single policy decision point.** Authorization is never reimplemented Suite-side: the caller's `Authorization` header is forwarded verbatim and ArcaQ's central PDP resolves permissions for the caller's identity (ADR-006). The Suite propagates identity; it does not recreate policy.
3. **Entry-point provenance is not caller-controlled.** The adapter always stamps `entry_point="suite"`; ArcaQ records it on the proposal and every `CE-*` change event, and OLM ChangeEvents carry `plm:entryPoint` (`direct`|`suite`) alongside `plm:triggeredBy` (actor identity) — arcaq PRs #2 and #4.
4. **Gates are entry-point-independent.** Turtle syntax (422 at submit), SHACL contracts (409 at deployment), OLM lifecycle (semver, four-eyes, quorum) apply identically whatever the entry point.
5. **Graceful degradation.** Null by default, short timeout, transport failure → `degraded` result; a down ArcaQ never blocks a Suite business flow.

Deliverables:
1. `adapters/ontology/` — `OntologyWriteAdapter` Protocol + `NullOntologyWriteAdapter` + `ArcaqOntologyWriteAdapter` (Http), opt-in via `ARCA_ONTOLOGY_WRITE_ADAPTER`. ✅ merged in arca-platform.
2. `contracts/ontology/` + `schemas/ontology/` — versioned OpenAPI + JSON schemas of the change-proposal surface. ✅ merged in arca-platform.
3. Per-module adoption: every module that produces ontology changes routes them through the adapter (flagged in module audits; e.g. cockpit contributions, pack workflows). ✅ adoptions: `arca-hub` cockpit (arca-hub PR #3) — `POST /api/v1/ontology/change-proposals`; `arca-packs` install (arca-packs PR #5, ADR-009) — pack ontology artifacts proposed to the funnel with `entry_point="suite"` on real installs; `arca-flow` definitions (arca-flow PR #2, ADR-010) — every workflow definition registration proposes its OLM entity (`WorkflowDefinition_<slug>`) to the funnel, with the raw `Authorization` header forwarded verbatim from both REST and MCP, outcome recorded per definition and audited as `ontology.change_proposed`.

Acceptance criteria: Null test (disabled = no call, business flow unblocked) + Http test (contract payload validated, entry_point forced to "suite", identity forwarded verbatim); falsification = captured-request assertions proving no payload can reach ArcaQ through this adapter without `entry_point="suite"` and that identity propagation cannot be silently dropped.

---

*References: `docs/integration/arcaq-linkage-audit.md` (2026-09-14), ArcaQ/ArcaX audit (2026-09-19), optimal reward-hacking analysis (2026-09-20), ArcaQ/ArcaX flaw register (2026-09-20).*
