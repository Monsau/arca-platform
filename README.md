# Arca Platform

> Arca Platform provides the deployment-neutral shared runtime foundation and technical interoperability contracts of Arca Suite. ArcaQ understands, remembers and reasons. ArcaX connects, secures, governs and executes. Arca Platform enables these autonomous products to operate consistently without absorbing their domain responsibilities.

## 1. Product name and concise positioning

**Arca Platform** is the deployment-neutral shared runtime foundation of Arca Suite. It defines the common technical contracts, conventions and adapters that allow ArcaQ, ArcaX, Arca Flow, Arca Hub, Arca Exchange, Arca Packs, Arca Trust, Arca Studio, Arca Bench and Arca Cert to operate as an integrated suite without becoming a monolith.

## 2. Mission

Provide the common runtime capabilities and stable technical contracts required by every Arca Suite product, while preserving the autonomy, release lifecycle and domain ownership of each product.

## 3. Scope

Arca Platform defines and may provide:

- Platform identity integration contracts.
- Service identity and workload identity abstractions.
- Configuration contracts and conventions.
- Secret-provider abstractions.
- Service discovery contracts.
- Health, readiness and liveness conventions.
- Telemetry and observability contracts (metrics, traces, logs).
- Event backbone abstractions and common messaging contracts.
- Audit-event contracts.
- Policy integration points.
- Platform-level metadata and service registration.
- Shared runtime SDKs and internal libraries.
- Platform bootstrap APIs.
- Lifecycle and capability discovery.
- Compatibility and version information.
- Common error models and API conventions.
- Cross-product technical interoperability contracts.
- Deployment-neutral reference configuration.
- Local development adapters and test fixtures.

## 4. Explicit non-goals

Arca Platform is **not**:

- A business application.
- A replacement for ArcaQ (no reasoning, ontology or knowledge graph).
- A replacement for ArcaX (no MCP gateway, execution governance or agent mediation).
- An agent orchestration engine.
- A decision engine.
- A knowledge platform.
- A Kubernetes deployment repository (that is `arca-platform-k8s`).
- A container for the source code of other Arca products.
- A central monolith into which all modules are merged.

## 5. Relationship with ArcaQ

ArcaQ owns sovereign knowledge, ontology, Knowledge Graph, CAG, Second Brain, institutional memory, contextual reasoning, explainability and human validation.

Arca Platform provides the technical contracts ArcaQ consumes to publish decision packages, expose health status, emit audit events and integrate with the event backbone. Arca Platform does not own ArcaQ's reasoning or ontology.

## 6. Relationship with ArcaX

ArcaX owns Enterprise MCP Gateway capabilities, Unified Agentic Mediation, connector governance, execution governance, security enforcement, controlled execution and execution observability.

Arca Platform provides the technical contracts ArcaX consumes to register capabilities, discover services, emit telemetry and integrate with identity and secret providers. Arca Platform does not own ArcaX's mediation, security enforcement or governance decisions.

## 7. Relationship with other Arca products

The following products remain autonomous:

- ArcaQ
- ArcaX
- Arca Flow
- Arca Decision Room
- Arca Hub
- Arca Studio
- Arca Exchange
- Arca Packs
- Arca Trust
- Arca Bench
- Arca Cert

Each product owns its business logic, APIs, data model, persistence, domain events, lifecycle, release process, security boundary, deployment-neutral repository and Kubernetes repository. Arca Platform exposes neutral contracts that each product may consume or implement while retaining ownership of its domain capabilities.

## 8. Platform capability domains

| Domain | Contract location | Adapter location |
|---|---|---|
| Identity | `contracts/identity/` | `adapters/identity/` |
| Configuration | `contracts/configuration/` | `adapters/configuration/` |
| Secrets | `contracts/secrets/` | `adapters/secrets/` |
| Observability | `contracts/observability/` | `adapters/observability/` |
| Events / Messaging | `contracts/events/` | `adapters/messaging/` |
| Audit | `contracts/audit/` | `adapters/audit/` |
| Health | `contracts/health/` | `adapters/health/` |
| Discovery | `contracts/discovery/` | `adapters/discovery/` |
| Lifecycle | `contracts/lifecycle/` | `adapters/lifecycle/` |

## 9. Deployment-neutral architecture

Arca Platform is infrastructure-neutral. Kubernetes, Kafka, OpenTelemetry, Vault, External Secrets Operator, Istio, KEDA, Keycloak and any equivalent technology are treated as adapters or deployment implementations, not as the definition of Arca Platform itself.

`arca-platform-k8s` is the Kubernetes implementation. It selects and deploys the adapters used by a specific environment without redefining the contracts.

## 10. Platform contracts

Platform contracts are versioned, language-neutral definitions stored in `contracts/` and `schemas/`:

- **Interface contracts** describe what a product or adapter must expose.
- **Event schemas** describe the shape of cross-product events.
- **Audit schemas** describe the shape of audit records.
- **Configuration schemas** describe valid platform configuration.
- **Service descriptors** describe how a service registers and is discovered.

Contracts are stable. Changes follow semantic versioning and require an ADR.

## 11. Adapter model

An adapter implements a platform contract for a specific technology. Examples:

- Kafka adapter for the events contract.
- OpenTelemetry adapter for the observability contract.
- Vault adapter for the secrets contract.
- Kubernetes adapter for the lifecycle contract.

Adapters live in `adapters/` and may have reference implementations. Product teams may provide their own adapter if it satisfies the contract.

## 12. Repository layout

```text
arca-platform/
├── README.md
├── LICENSE
├── CODEOWNERS
├── docs/
│   ├── architecture/
│   ├── contracts/
│   ├── integration/
│   └── adr/
├── contracts/
│   ├── identity/
│   ├── configuration/
│   ├── secrets/
│   ├── observability/
│   ├── events/
│   ├── audit/
│   ├── health/
│   ├── discovery/
│   └── lifecycle/
├── schemas/
│   ├── events/
│   ├── audit/
│   ├── configuration/
│   └── service-descriptors/
├── sdk/
│   ├── common/
│   └── platform-client/
├── services/
│   ├── platform-registry/
│   ├── capability-discovery/
│   └── bootstrap/
├── adapters/
│   ├── identity/
│   ├── secrets/
│   ├── messaging/
│   └── observability/
├── config/
│   ├── defaults/
│   └── examples/
├── tests/
│   ├── contract/
│   ├── integration/
│   └── fixtures/
└── scripts/
```

Only directories justified by actual or explicitly planned capabilities are populated. Capabilities marked as planned are documented but not implemented as production code.

## 13. Local development principles

- Use the contracts and SDKs defined in this repository.
- Use test fixtures in `tests/fixtures/` to simulate platform dependencies.
- Do not require a Kubernetes cluster for unit or contract tests.
- Local adapters (e.g., in-memory messaging) are provided for development and testing.

## 14. Testing strategy

- **Contract tests** verify that products and adapters satisfy platform contracts.
- **Integration tests** verify that adapters work against real or containerized infrastructure in CI.
- **Fixtures** provide stable inputs for local development and contract tests.

## 15. Security principles

- No secret is committed to this repository.
- Contracts define how secrets are referenced, not their values.
- Identity and workload identity are abstracted; concrete providers are adapters.
- Audit contracts require non-repudiation and traceability.

## 16. Versioning and compatibility

- Platform contracts follow semantic versioning.
- Breaking contract changes require a major version bump and an ADR.
- Products declare the platform contract versions they implement.
- Compatibility matrices are published in `docs/integration/`.

## 17. Implemented versus planned capabilities

| Capability | Status | Evidence |
|---|---|---|
| Repository split from `arca-platform-k8s` | Implemented | This README and ADR-005 |
| Contract directory structure | Implemented | `contracts/`, `schemas/` |
| SDK directory structure | Implemented | `sdk/` |
| Adapter directory structure | Implemented | `adapters/` |
| Service skeleton structure | Implemented | `services/` |
| Configuration defaults and examples | Implemented | `config/` |
| Test structure | Implemented | `tests/` |
| Identity contract | Planned | `contracts/identity/` placeholder |
| Secrets contract | Planned | `contracts/secrets/` placeholder |
| Observability contract | Planned | `contracts/observability/` placeholder |
| Events contract | Planned | `contracts/events/` placeholder |
| Audit contract | Planned | `contracts/audit/` placeholder |
| Health contract | Planned | `contracts/health/` placeholder |
| Discovery contract | Planned | `contracts/discovery/` placeholder |
| Lifecycle contract | Planned | `contracts/lifecycle/` placeholder |
| Platform registry service | Planned | `services/platform-registry/` placeholder |
| Capability discovery service | Planned | `services/capability-discovery/` placeholder |
| Bootstrap service | Planned | `services/bootstrap/` placeholder |
| Reference adapters | Planned | `adapters/*/` placeholders |
| Contract test suite | Planned | `tests/contract/` placeholder |

## 18. Ownership and contribution rules

- Platform team owns this repository.
- Changes to platform contracts require an ADR and broad review.
- Product teams may propose contract additions but cannot unilaterally change contracts.
- All contract tests must pass before merge.
- No secret may be committed.

## 19. Link to arca-platform-k8s

For Kubernetes deployment, composition and operational configuration, see:

[https://github.com/Monsau/arca-platform-k8s](https://github.com/Monsau/arca-platform-k8s)

## 20. Canonical positioning statement

> Arca Platform provides the deployment-neutral shared runtime foundation and technical interoperability contracts of Arca Suite. ArcaQ understands, remembers and reasons. ArcaX connects, secures, governs and executes. Arca Platform enables these autonomous products to operate consistently without absorbing their domain responsibilities.
