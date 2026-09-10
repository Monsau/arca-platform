# Incident Runbook — Arca Platform

1. Identify the failing product from the platform overlay build or deployment.
2. Check the product's own runbooks in `subprojects/<product>-k8s/docs/runbooks/`.
3. Pin or roll back the submodule SHA for that product.
4. Re-apply the platform overlay: `kubectl apply -k clusters/server01/overlays/arcasuite`.
5. Record the action in the platform incident log.

# Rollback Runbook — Arca Platform

1. Revert the platform commit that updated the submodule(s).
2. Run `git submodule update` to restore the pinned SHAs.
3. Re-apply the overlay and verify probes.

# Forensic Runbook — Arca Platform

1. Collect git history of submodule SHA changes around the incident window.
2. Correlate with product audit trails and evidence bundles.
3. Preserve the platform overlay state as an artifact.

# Offboarding Runbook — Arca Platform

1. Remove the leaver from `CODEOWNERS` and platform RBAC.
2. Rotate any platform-level credentials (Vault, cluster access).
3. Audit submodule update history for unauthorized changes.
