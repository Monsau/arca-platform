# Arca Platform — Platform Orchestration Root

This repository is the **platform orchestration root** for Arca Suite V2.3.
It does not contain business logic; it references every product `-k8s`
repository as a git submodule and provides the shared platform layer that
deploys the whole suite into the `arcasuite` namespace on `server01`.

## Layout

```
arca-platform/
├── subprojects/              # git submodules pointing to each -k8s repo
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
│           └── arcasuite/
│               └── kustomization.yaml  # deploy all products into arcasuite
├── platform/shared/                    # shared infra config (Kafka, OTel, Vault backend)
└── docs/adr/                           # platform-level ADRs
```

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

# Build the platform manifest for server01
cd clusters/server01/overlays/arcasuite
kustomize build .

# Apply (requires kubectl context pointing to server01)
kubectl apply -k .
```

## Rules

- The `arcasuite` namespace is the single deployment target for server01.
- Each product keeps its own service account, RBAC, NetworkPolicies and mTLS
  settings; the platform overlay only changes the namespace target.
- No secret is stored in this repository. External Secrets Operator pulls
  runtime secrets from Vault.
- Shared infrastructure (Kafka, OTel collector, Vault backend) is configured
  in `platform/shared/` and must be present before applying the overlay.

## Owners

See `CODEOWNERS`.
