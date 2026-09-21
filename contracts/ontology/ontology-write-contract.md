# Arca Platform — Ontology Write Contract

Version 1.0.0 — 2026-09-21

## Purpose

This contract is the **Suite-side, versioned description** of the ArcaQ
centralized ontology write surface. Suite modules submit ontology changes
*through* this surface as clients — they never write to the knowledge store
directly.

Source of truth on the product side: `arcaq-api`,
`modules/arcaq-api/src/api/routers/ontology_ops.py` (write funnel merged in
arcaq PR #2, entry-point provenance extended in arcaq PR #4). Per golden
rule #1, this repo never imports arcaq code: the contract below is the only
integration point.

## Endpoint

`POST {arcaq-base-url}/api/v1/ontology-ops/change-proposals`

See `openapi.yaml` in this directory for the machine-readable form, and
`../../schemas/ontology/` for the JSON schemas.

## Binding rules

1. **Single physical writer.** Only ArcaQ pipelines persist ontology data
   (Jena/Fuseki). A Suite module is a client of the endpoint above — never a
   second writer. Two chains of custody would diverge (dual-SOC finding of
   the 2026-09-19 audit).
2. **Single policy decision point (PDP).** The Suite does not reimplement
   authorization. The caller's `Authorization` header is forwarded verbatim
   and ArcaQ resolves permissions for the caller's identity through its
   central ReBAC (see `docs/adr/ADR-006-policy-contract.md`: products act on
   policy decisions, they do not own the policy engine). Suite-side
   permission management is "identical and propagated": the same identity,
   the same PDP, whatever the entry point.
3. **Entry-point provenance is not caller-controlled.** Every Suite-originated
   submission carries `entry_point = "suite"`. The ArcaQ enum is closed
   (`"direct" | "suite"`) and enforced at the API, at deployment (SHACL
   gate), and in CI. OLM lifecycle transitions carry the same trace via
   `plm:entryPoint` on ChangeEvents (arcaq PR #4).
4. **Gates are entry-point-independent.** Turtle syntax validation at submit
   (HTTP 422 on invalid), SHACL contract validation at submit and deployment
   (HTTP 409 on violation), OLM lifecycle (semver, four-eyes, quorum) — the
   same gates apply whether the writer is a direct ArcaQ user or a Suite
   module.
5. **Graceful degradation.** The Suite-side adapter (`adapters/ontology/`)
   uses a short timeout and maps any transport failure to a `degraded`
   result. ArcaQ being down never blocks a Suite business flow.

## Request

Mirrors the ArcaQ `ChangeProposalIn` model:

| Field | Type | Required | Notes |
|---|---|---|---|
| `change_type` | string | yes | `add_class` \| `add_property` \| `modify_label` \| `deprecate` \| `delete` |
| `concept_uri` | string (URI) | yes | Full URI of the affected concept |
| `impact_level` | string | yes | `patch` \| `minor` \| `major` |
| `description` | string | yes | Human-readable description |
| `proposed_ttl` | string (Turtle) | no | Syntax validated at submit (422) |
| `proposer` | string | no | Defaults to the authenticated caller |
| `entry_point` | string | yes | Always `"suite"` from the Suite adapter (default `"direct"` for direct ArcaQ users) |

## Response

HTTP 201 with a proposal object: `id`, `state` (`draft`), `proposer`,
`entry_point`, `ttl_validation` (syntax + SHACL pre-check), timestamps.
Subsequent lifecycle (review, approval, deployment) stays in ArcaQ — the
Suite does not reimplement workflow either.

## Audit

Every deployed proposal emits a structured change event (`CE-*`) carrying
`entry_point`, the proposer/reviewer/deployer identities and the SHA-256 of
the proposed Turtle, persisted to a JSONL log and exposed via
`GET /api/v1/ontology-ops/change-events?entry_point=suite`. OLM lifecycle
ChangeEvents answer the same question via `plm:entryPoint` (`direct`|`suite`)
alongside `plm:triggeredBy` (actor identity).

## Falsification hooks

The Suite-side adapter is tested with captured-request assertions proving:

- no payload can reach ArcaQ through the adapter without
  `entry_point == "suite"`;
- the caller's `Authorization` header is forwarded verbatim (identity
  propagation), never rewritten;
- transport failure degrades, never raises.
