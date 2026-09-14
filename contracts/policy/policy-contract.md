# Arca Platform Policy Contract

> Deployment-neutral RBAC/ABAC policy contract for the Arca Suite.

## 1. Purpose

This contract defines how Arca Suite products evaluate access and authorization decisions without owning the policy engine. It separates the policy evaluation interface from concrete implementations such as OPA, Rego, Cedar, or custom RBAC stores.

## 2. Concepts

| Concept | Definition |
|---|---|
| **Role** | Named set of permissions assigned to a subject. |
| **Permission** | Allowed action on a resource. |
| **Resource** | Entity being accessed (asset, decision, workflow, etc.). |
| **Action** | Operation requested (`read`, `write`, `execute`, `delete`). |
| **Attribute** | Contextual property of subject, resource, action or environment. |
| **Decision** | Result of policy evaluation: `permit`, `deny` or `indeterminate`. |

## 3. Policy evaluation request

```json
{
  "subject": {
    "id": "user-123",
    "roles": ["decision-sealer"],
    "attributes": {"department": "risk"}
  },
  "resource": {
    "type": "decision",
    "id": "d-abc"
  },
  "action": "seal",
  "environment": {
    "time": "2026-09-14T10:00:00Z",
    "source_ip": "10.0.0.1"
  }
}
```

## 4. Policy evaluation response

```json
{
  "decision": "permit",
  "reason": "role allows seal on decisions in risk department",
  "obligations": []
}
```

## 5. Adapter requirements

A policy adapter:

1. Accepts a `PolicyEvalRequest`.
2. Returns a `PolicyEvalResponse` with decision `permit`, `deny` or `indeterminate`.
3. Is stateless with respect to product business logic; it may call OPA, Rego, Cedar, or a static map.
4. Does not leak provider-specific types into product code.

## 6. Version

- Version: 1.0.0
- Contract owner: @arca-suite/platform
