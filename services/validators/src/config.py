"""Validators configuration — every value is env-driven, no plaintext secrets.

Mirrors the portal philosophy (services/portal/src/config.py): the issuer stays
the public URL (iss claim), while the JWKS endpoint may be overridden with an
in-cluster plain-HTTP URL for reachability.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


#: Bundled SHACL shapes + core background graphs, shipped with the image.
BUNDLED_SHAPES_DIR = Path(__file__).resolve().parent.parent / "shapes"


@dataclass(frozen=True)
class Settings:
    # OIDC (Keycloak) — RS256 SSO tokens, same model as the portal.
    oidc_issuer: str = field(default_factory=lambda: _env("VALIDATE_OIDC_ISSUER"))
    oidc_jwks_url: str = field(default_factory=lambda: _env("VALIDATE_OIDC_JWKS_URL", ""))
    oidc_audience: str = field(default_factory=lambda: _env("VALIDATE_OIDC_AUDIENCE", "arca-suite"))
    # JWKS cache TTL; Keycloak rotates signing keys rarely.
    jwks_ttl_seconds: int = field(
        default_factory=lambda: int(_env("VALIDATE_OIDC_JWKS_TTL", "900"))
    )
    # Optional override for the bundled shapes directory (tests, local dev).
    shapes_dir: str = field(
        default_factory=lambda: _env("VALIDATE_SHAPES_DIR", str(BUNDLED_SHAPES_DIR))
    )

    @property
    def issuer(self) -> str:
        return self.oidc_issuer.rstrip("/")

    @property
    def jwks_url(self) -> str:
        return self.oidc_jwks_url or f"{self.issuer}/protocol/openid-connect/certs"


def get_settings() -> Settings:
    return Settings()
