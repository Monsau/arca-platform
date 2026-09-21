"""Portal service — central Arca Suite UI.

The portal is the single human entry point of the suite: it authenticates
users against Keycloak (OIDC authorization-code flow), renders the shared
shell (sidebar navigation across suite modules) and reverse-proxies module
UIs and APIs under /m/<module>/, attaching the caller's access token so
modules receive a consistent identity.

No mock data: every figure rendered by the shell comes from a live module
call, and every module frame shows the module's own UI.
"""
