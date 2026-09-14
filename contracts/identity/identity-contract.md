# Arca Platform Identity Contract

> Deployment-neutral identity and SSO contract for the Arca Suite.

## 1. Purpose

This contract defines how Arca Suite products consume identity information without coupling to a specific Identity Provider (IdP). It covers:

- OIDC discovery convention.
- JWT claims model.
- Service-account and workload-identity abstraction.

No concrete IdP (Keycloak, Entra ID, Okta, etc.) is mandated. Products consume the neutral abstractions defined here; adapters map them to the chosen provider.

## 2. OIDC discovery convention

Each product exposes and/or trusts OIDC discovery metadata at a well-known path:

```text
{issuer}/.well-known/openid-configuration
```

The response MUST be a JSON object compliant with [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html). Minimum required fields:

| Field | Type | Description |
|---|---|---|
| `issuer` | string | Canonical issuer URL. |
| `authorization_endpoint` | string | URL of the authorization endpoint. |
| `token_endpoint` | string | URL of the token endpoint. |
| `jwks_uri` | string | URL of the JWKS endpoint. |
| `response_types_supported` | array | e.g. `["code"]`. |
| `subject_types_supported` | array | e.g. `["public"]`. |
| `id_token_signing_alg_values_supported` | array | e.g. `["RS256"]`. |

## 3. JWT claims model

Identity tokens consumed by Arca products MUST expose at least the following claims:

| Claim | Required | Description |
|---|---|---|
| `sub` | yes | Stable subject identifier (OIDC subject). |
| `iss` | yes | Issuer identifier. |
| `aud` | yes | Audience, which MUST include the product's `oidc_audience`. |
| `exp` | yes | Expiration time. |
| `iat` | yes | Issued-at time. |
| `roles` | no | Array of RBAC role names. |
| `groups` | no | Array of group names. |
| `scope` | no | Space-separated OAuth2 scopes. |

Products MUST validate `iss`, `aud`, `exp` and signature. They MAY enforce `nbf` if present.

## 4. Service-account / workload identity abstraction

Machine-to-machine identities are represented uniformly regardless of whether they are OAuth2 client credentials, SPIFFE identities, Kubernetes service accounts, or platform workload identities.

```text
WorkloadIdentity
  - workload_id: stable URI or URN identifier
  - issuer: identity provider or trust domain
  - service_account: human-readable account name
  - attributes: map of extra claims (namespace, cluster, SPIFFE path, etc.)
```

A `ServiceAccount` is a specialization of `WorkloadIdentity` intended for long-lived service principals:

```text
ServiceAccount
  - account_id
  - account_name
  - issuer
  - scopes
```

## 5. Adapter requirements

An identity adapter:

1. Accepts a raw token (JWT or opaque reference).
2. Validates it against the configured issuer and JWKS.
3. Returns a normalized `IdentityToken` or `WorkloadIdentity`.
4. Never exposes provider-specific internals to product code.

## 6. Version

- Version: 1.0.0
- Contract owner: @arca-suite/platform
