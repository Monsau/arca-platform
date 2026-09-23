"""JWT validation for the validators service (RS256 Keycloak SSO tokens).

Security by design: every /api/v1/validate call must carry a bearer token whose
signature, expiry, issuer and audience are all verified against the realm JWKS
before any validation work happens. There is no anonymous validation path.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import httpx
import jwt

from .config import Settings

logger = logging.getLogger(__name__)


class AuthRejected(Exception):
    """Raised when a bearer token cannot be accepted (any reason)."""


class TokenValidator:
    """Verifies RS256 JWTs against the realm JWKS, cached with a TTL."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self._http = http or httpx.AsyncClient(timeout=10.0)
        self._owns_http = http is None
        self._lock = threading.Lock()
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at = 0.0

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def validate(self, token: str) -> dict[str, Any]:
        """Verify signature + exp + iss + aud; return the claims on success."""
        if not token:
            raise AuthRejected("missing bearer token")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise AuthRejected(f"malformed token header: {exc}") from exc
        kid = header.get("kid")
        if not kid:
            raise AuthRejected("token header has no kid")
        jwks = await self._get_jwks()
        jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if jwk is None:
            raise AuthRejected(f"no matching JWKS key for kid {kid!r}")
        try:
            key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            claims = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                audience=self.settings.oidc_audience,
                issuer=self.settings.issuer,
                # leeway is intentionally 0: stale SSO tokens are rejected.
                leeway=0,
                options={"require": ["exp", "iss", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthRejected("token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthRejected(f"token rejected: {exc}") from exc
        return claims

    async def _get_jwks(self) -> dict[str, Any]:
        # Keycloak rotates signing keys rarely; cache for the configured TTL.
        with self._lock:
            if (
                self._jwks
                and time.time() - self._jwks_fetched_at < self.settings.jwks_ttl_seconds
            ):
                return self._jwks
        resp = await self._http.get(self.settings.jwks_url)
        resp.raise_for_status()
        jwks = resp.json()
        with self._lock:
            self._jwks = jwks
            self._jwks_fetched_at = time.time()
        return jwks
