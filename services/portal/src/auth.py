"""OIDC authentication (Keycloak authorization-code flow) and sessions.

Server-side session store keeps Keycloak tokens out of the cookie; the
browser only holds a signed session id. Redis is used when PORTAL_REDIS_URL
is set (multi-replica safe); otherwise an in-process store is used, which
is safe only for a single replica.
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from typing import Any

import httpx
import jwt
from itsdangerous import BadSignature, URLSafeSerializer

from .config import Settings

logger = logging.getLogger(__name__)


class SessionStore:
    """Session id -> {access_token, id_claims, expires_at} with TTL."""

    def __init__(self, redis_url: str = "", ttl: int = 28800):
        self._ttl = ttl
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        self._redis = None
        if redis_url:
            try:
                import redis as redis_lib

                self._redis = redis_lib.from_url(
                    redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
                )
                self._redis.ping()
                logger.info("portal sessions backed by redis")
            except Exception as exc:  # noqa: BLE001
                logger.warning("portal redis unavailable (%s), falling back to memory", exc)
                self._redis = None

    @staticmethod
    def _key(sid: str) -> str:
        return f"arca-portal:session:{sid}"

    def put(self, sid: str, payload: dict[str, Any]) -> None:
        payload = dict(payload, expires_at=time.time() + self._ttl)
        if self._redis:
            self._redis.setex(self._key(sid), self._ttl, json.dumps(payload))
            return
        with self._lock:
            self._purge()
            self._data[sid] = payload

    def get(self, sid: str) -> dict[str, Any] | None:
        if self._redis:
            raw = self._redis.get(self._key(sid))
            return json.loads(raw) if raw else None
        with self._lock:
            payload = self._data.get(sid)
        if not payload or payload.get("expires_at", 0) < time.time():
            self.delete(sid)
            return None
        return payload

    def delete(self, sid: str) -> None:
        if self._redis:
            self._redis.delete(self._key(sid))
            return
        with self._lock:
            self._data.pop(sid, None)

    def _purge(self) -> None:
        now = time.time()
        for sid in [s for s, p in self._data.items() if p.get("expires_at", 0) < now]:
            self._data.pop(sid, None)


class AuthError(Exception):
    """Raised when the OIDC flow cannot complete."""


class OIDCClient:
    """Authorization-code flow against a Keycloak realm."""

    def __init__(self, settings: Settings, store: SessionStore):
        self.settings = settings
        self.store = store
        self._http = httpx.AsyncClient(timeout=15.0)
        self._signer = URLSafeSerializer(
            settings.session_secret or secrets.token_hex(32), salt="arca-portal-session"
        )
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at = 0.0

    # -- cookie ------------------------------------------------------------
    def encode_cookie(self, sid: str) -> str:
        return self._signer.dumps(sid)

    def decode_cookie(self, cookie_value: str | None) -> str | None:
        if not cookie_value:
            return None
        try:
            sid = self._signer.loads(cookie_value)
        except BadSignature:
            return None
        return sid if isinstance(sid, str) else None

    # -- OIDC flow ---------------------------------------------------------
    def authorize_redirect(self, state: str) -> str:
        s = self.settings
        params = {
            "client_id": s.oidc_client_id,
            "redirect_uri": s.oidc_redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
        query = httpx.QueryParams(params)
        return f"{s.authorize_url}?{query}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        s = self.settings
        resp = await self._http.post(
            s.token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": s.oidc_redirect_uri,
                "client_id": s.oidc_client_id,
                "client_secret": s.oidc_client_secret,
            },
        )
        if resp.status_code != 200:
            raise AuthError(f"token endpoint returned {resp.status_code}: {resp.text[:200]}")
        tokens = resp.json()
        claims = await self.validate_id_token(tokens["id_token"])
        return {"tokens": tokens, "claims": claims}

    async def validate_id_token(self, id_token: str) -> dict[str, Any]:
        jwks = await self._get_jwks()
        header = jwt.get_unverified_header(id_token)
        key = jwt.algorithms.RSAAlgorithm.from_jwk(
            json.dumps(next(k for k in jwks["keys"] if k["kid"] == header["kid"]))
        )
        claims = jwt.decode(
            id_token,
            key=key,
            algorithms=["RS256"],
            audience=self.settings.oidc_client_id,
            issuer=self.settings.issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
        return claims

    async def _get_jwks(self) -> dict[str, Any]:
        # Keycloak rotates signing keys rarely; cache 5 minutes.
        if self._jwks and time.time() - self._jwks_fetched_at < 300:
            return self._jwks
        resp = await self._http.get(self.settings.jwks_url)
        resp.raise_for_status()
        self._jwks = resp.json()
        self._jwks_fetched_at = time.time()
        return self._jwks

    # -- session lifecycle ---------------------------------------------------
    def create_session(self, tokens: dict[str, Any], claims: dict[str, Any]) -> str:
        sid = secrets.token_urlsafe(32)
        self.store.put(
            sid,
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token", ""),
                "id_token": tokens.get("id_token", ""),
                "claims": claims,
            },
        )
        return sid

    def load_session(self, cookie_value: str | None) -> dict[str, Any] | None:
        sid = self.decode_cookie(cookie_value)
        if not sid:
            return None
        return self.store.get(sid)

    def destroy_session(self, cookie_value: str | None) -> str | None:
        """Drop the session and return the Keycloak id_token_hint if any."""
        sid = self.decode_cookie(cookie_value)
        if not sid:
            return None
        payload = self.store.get(sid)
        self.store.delete(sid)
        if payload:
            return payload.get("id_token") or None
        return None
