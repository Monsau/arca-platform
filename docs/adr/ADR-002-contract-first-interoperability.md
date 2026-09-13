# ADR-002: Contract-First Cross-Product Interoperability

- Status: Accepted
- Date: 2026-09-13
- Owners: @arca-suite/platform

## Context

Arca Suite products must integrate without hidden coupling or direct database access. The integration mechanism must be explicit, versioned and auditable.

## Decision

All cross-product technical interoperability is defined by platform contracts. Products interact through REST, GraphQL, MCP, Kafka events, OOC artifacts and explicit versioned contracts. Direct code import and direct database access are forbidden.

## Consequences

- Products remain independently deployable.
- Integration failures are detectable by contract tests.
- Contract versions must be managed carefully.

## Compliance

- No product imports another product's internal code.
- No product accesses another product's database.
