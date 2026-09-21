"""Portal configuration — every value is env-driven, no plaintext secrets."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    # OIDC (Keycloak)
    oidc_issuer: str = field(default_factory=lambda: _env("PORTAL_OIDC_ISSUER"))
    oidc_client_id: str = field(default_factory=lambda: _env("PORTAL_OIDC_CLIENT_ID", "arca-suite-portal"))
    oidc_client_secret: str = field(default_factory=lambda: _env("PORTAL_OIDC_CLIENT_SECRET"))
    oidc_redirect_uri: str = field(default_factory=lambda: _env("PORTAL_OIDC_REDIRECT_URI"))
    # Back-channel endpoints may be overridden for in-cluster reachability:
    # the issuer stays the public URL (iss claim + authorize redirect), while
    # token/JWKS calls use a cluster-routable URL (plain HTTP service).
    oidc_token_url: str = field(default_factory=lambda: _env("PORTAL_OIDC_TOKEN_URL", ""))
    oidc_jwks_url: str = field(default_factory=lambda: _env("PORTAL_OIDC_JWKS_URL", ""))
    # Session cookie signing — generated per process when unset (sessions
    # invalidate on restart; set PORTAL_SESSION_SECRET for stability).
    session_secret: str = field(default_factory=lambda: _env("PORTAL_SESSION_SECRET"))
    session_cookie: str = "arca_suite_session"
    session_ttl_seconds: int = field(default_factory=lambda: int(_env("PORTAL_SESSION_TTL", "28800")))
    # Optional Redis session/token store (required for >1 replica).
    redis_url: str = field(default_factory=lambda: _env("PORTAL_REDIS_URL"))
    # Public base URL of the portal (used for post-logout redirect).
    public_base_url: str = field(default_factory=lambda: _env("PORTAL_PUBLIC_BASE_URL", ""))

    @property
    def issuer(self) -> str:
        return self.oidc_issuer.rstrip("/")

    @property
    def jwks_url(self) -> str:
        return self.oidc_jwks_url or f"{self.issuer}/protocol/openid-connect/certs"

    @property
    def token_url(self) -> str:
        return self.oidc_token_url or f"{self.issuer}/protocol/openid-connect/token"

    @property
    def authorize_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/auth"

    @property
    def end_session_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/logout"

    @property
    def configured(self) -> bool:
        return bool(self.oidc_issuer and self.oidc_client_secret and self.oidc_redirect_uri)


@dataclass(frozen=True)
class Module:
    """One suite module exposed in the portal navigation."""

    key: str
    name: str
    icon: str  # Material Icons ligature — must exist in the webfont (see F-AQ-11).
    service: str  # in-cluster service host (e.g. http://trust.arcasuite.svc.cluster.local)
    ui_base: str  # module UI mount path, proxied under /m/<key>
    description: str = ""


def load_modules() -> list[Module]:
    """Load the module registry from PORTAL_MODULES (JSON) or defaults.

    Defaults match the arcasuite namespace service topology on server01.
    """
    raw = _env("PORTAL_MODULES")
    if raw:
        data = json.loads(raw)
        return [Module(**m) for m in data]
    ns = "arcasuite.svc.cluster.local"
    return [
        Module("cockpit", "Hub Cockpit", "hub", f"http://arca-hub.{ns}", "/ui/", "Executive overview federated from Arca modules"),
        Module("trust", "Trust", "verified_user", f"http://trust.{ns}", "/ui/", "Posture, compliance and risk signals"),
        Module("bench", "Bench", "science", f"http://bench.{ns}", "/ui/", "Quality, performance and resilience lab"),
        Module("cert", "Cert", "workspace_premium", f"http://cert.{ns}", "/cert/", "Certification dossiers and SOC"),
        Module("studio", "Studio", "architecture", f"http://studio.{ns}", "/ui/", "Cognitive asset studio"),
        Module("exchange", "Exchange", "storefront", f"http://arca-exchange.{ns}", "/ui/", "Federated cognitive asset marketplace"),
        Module("decision-room", "Decision Room", "gavel", f"http://arca-decision-room.{ns}", "/ui/", "Collaborative decision workspace"),
        Module("flow", "Flow", "account_tree", f"http://arca-flow.{ns}", "/ui/", "Workflow runtime and state"),
        Module("packs", "Packs", "inventory_2", f"http://arca-packs-api.{ns}", "/ui/", "Certified capability packs"),
    ]
