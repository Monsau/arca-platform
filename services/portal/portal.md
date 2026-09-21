# Portal Service

The Arca Suite Portal is the **single human entry point** of the suite. It
provides one authenticated UI that groups every suite module behind a unified
navigation, instead of exposing one hostname and URL style per module.

## Responsibilities

- **Authentication**: OIDC authorization-code flow against the shared
  Keycloak realm (`tour-operator`, client `arca-suite-portal`). The portal is
  the suite's human authentication point; module UIs are only reachable
  through the authenticated proxy.
- **Shell**: sidebar navigation across the nine suite modules, user identity,
  theme toggle, module health overview. Design tokens follow the ArcaQ
  design system (`portal.css`) so the suite reads as one product.
- **Module proxy**: `/m/<module>/<path>` forwards to the module's in-cluster
  service, attaching the caller's Keycloak access token as `Authorization:
  Bearer`. Module pages are embedded via a fluid full-size frame served from
  the portal origin, so users never see per-module `/ui/` URLs.

## What the portal deliberately does not do

- No mock or synthetic data. The overview page probes each module's
  `/healthz` live and reports honest failures.
- No domain logic: the portal never re-interprets module data; the frame
  shows the module's own UI.
- No user management: identity lifecycle stays in Keycloak.

## Module registry

Modules default to the `arcasuite` namespace topology (see
`src/config.py:load_modules`). Override with the `PORTAL_MODULES` JSON env
when deploying elsewhere. Each entry:

| field       | meaning                                             |
|-------------|-----------------------------------------------------|
| `key`       | stable slug used in portal routes                   |
| `name`      | display name in the navigation                      |
| `icon`      | Material Icons ligature (must exist in the webfont) |
| `service`   | in-cluster base URL of the module service           |
| `ui_base`   | module UI mount path                                |
| `description` | one-line subtitle                                  |

## Configuration

| env                          | required | purpose                                   |
|------------------------------|----------|-------------------------------------------|
| `PORTAL_OIDC_ISSUER`         | yes      | Keycloak realm URL                        |
| `PORTAL_OIDC_CLIENT_ID`      | no       | defaults to `arca-suite-portal`           |
| `PORTAL_OIDC_CLIENT_SECRET`  | yes      | client secret (Kubernetes secret)         |
| `PORTAL_OIDC_REDIRECT_URI`   | yes      | e.g. `https://suite.arca.local/auth/callback` |
| `PORTAL_PUBLIC_BASE_URL`     | no       | used as post-logout redirect              |
| `PORTAL_SESSION_SECRET`      | no       | cookie signer (random per boot otherwise) |
| `PORTAL_REDIS_URL`           | no       | session store for multi-replica           |
| `PORTAL_MODULES`             | no       | JSON module registry override             |

## Operations notes

- Run **one replica** when `PORTAL_REDIS_URL` is unset: the OIDC `state`
  set and the memory session store are per-process. With Redis configured
  the session store is shared, but `state` remains per-process, so keep a
  single replica or move `state` to Redis before scaling.
- Sessions last 8 hours (`PORTAL_SESSION_TTL`).
- Icon ligatures are verified against the served webfont at deploy time
  (see F-AQ-11 in the ArcaQ register): the Google Fonts subset has dropped
  at least `database` and `sql`; never add an icon name without probing it.

## Phase 2 (planned)

- Remove the per-module dev auth bypasses (`*_AUTH_DISABLED`) and have each
  module validate the portal-forwarded JWT instead.
- Replace framed module UIs with natively integrated pages, module by
  module, reusing this design system.
