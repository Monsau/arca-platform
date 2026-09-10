# Arca Platform — Platform Orchestration Root

This repository is the **platform orchestration root** for Arca Suite V2.3.
It does not contain business logic; it references every product `-k8s`
repository as a git submodule and provides the shared platform layer that
deploys the suite on `server01`.

## Layout

```
arca-platform/
├── subprojects/              # git submodules pointing to each -k8s repo
│   ├── arcaq-k8s/            # foundation platform (referenced for visibility)
│   ├── arcax-k8s/            # foundation platform (referenced for visibility)
│   ├── arca-flow-k8s/
│   ├── arca-decision-room-k8s/
│   ├── arca-hub-k8s/
│   ├── arca-exchange-k8s/
│   ├── arca-packs-k8s/
│   ├── arca-trust-k8s/
│   ├── arca-studio-k8s/
│   ├── arca-bench-k8s/
│   └── arca-cert-k8s/
├── clusters/
│   └── server01/
│       ├── base/
│       │   └── namespace.yaml          # arcasuite namespace
│       └── overlays/
│           ├── platform/
│           │   └── kustomization.yaml  # shared infra in the platform namespace
│           └── arcasuite/
│               └── kustomization.yaml  # deploy all suite modules into arcasuite
├── platform/shared/                    # shared services config (Kafka, OTel, Vault/ESO)
└── docs/adr/                           # platform-level ADRs
```

## Namespace model

- `arcasuite` — single workload namespace for the suite modules on server01.
- `platform` — shared infrastructure namespace (Kafka, OTel collector, Vault,
  External Secrets Operator backend).

Each product `-k8s` base is namespace-agnostic. The platform overlay sets the
deployment target to `arcasuite`; the product's own overlays create the
namespace when deploying standalone.

## Why submodules?

Each product is autonomous and owns its own `-k8s` repository. The platform
repo only **references** pinned versions of those repositories via git
submodules. This keeps the platform contract explicit, auditable and
reproducible, without copying or forking the product manifests.

## Deploy

```bash
# Clone including all submodules
git clone --recurse-submodules git@github.com:Monsau/arca-platform.git

# Or, after a normal clone:
git submodule update --init --recursive

# 1. Shared platform infrastructure (Kafka, OTel, Vault backend)
cd clusters/server01/overlays/platform
kubectl apply -k .

# 2. Suite workloads in the arcasuite namespace
cd ../arcasuite
kubectl apply -k .
```

## Validate locally

```bash
kubectl kustomize clusters/server01/overlays/platform
kubectl kustomize clusters/server01/overlays/arcasuite
```

> `kustomize` CLI is not required; `kubectl` has it built-in.

## Rules

- The `arcasuite` namespace is the single deployment target for suite modules
  on server01.
- Each product keeps its own service account, RBAC, NetworkPolicies and mTLS
  settings; the platform overlay only changes the namespace target.
- No secret is stored in this repository. External Secrets Operator pulls
  runtime secrets from Vault.
- Shared infrastructure lives in the `platform` namespace and is deployed
  before the suite workloads.

## Owners

See `CODEOWNERS`.
