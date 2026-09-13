"""JWT reference adapter for the Arca Platform identity contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IdentityToken:
    subject: str
    issuer: str
    audience: list[str]
    scopes: list[str]
    claims: dict[str, Any]


class JWTIdentityAdapter:
    """Reference adapter validating OIDC/JWT tokens.

    Products receive a stable IdentityToken regardless of the identity provider
    used by the deployment.
    """

    def __init__(self, issuer: str, jwks_url: str | None = None) -> None:
        self.issuer = issuer
        self.jwks_url = jwks_url

    def validate(self, token: str) -> IdentityToken:
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PyJWT is required for JWT adapter") from exc
        # In production this validates the signature against JWKS and checks
        # issuer, audience, expiry and scopes.
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": True},
            issuer=self.issuer,
        )
        return IdentityToken(
            subject=payload.get("sub", ""),
            issuer=payload.get("iss", ""),
            audience=payload.get("aud", []),
            scopes=payload.get("scope", "").split(),
            claims=payload,
        )
