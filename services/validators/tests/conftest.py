"""Shared fixtures: sys.path setup, test RSA key, JWKS, signed tokens, authed client."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

# Environment must be set before src.main is imported (Settings is frozen at
# import time). These mirror the staging values from the deployment docs.
os.environ.setdefault("VALIDATE_OIDC_ISSUER", "https://auth.staging.server01/realms/tour-operator")
os.environ.setdefault("VALIDATE_OIDC_AUDIENCE", "arca-suite")

SERVICES_VALIDATORS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICES_VALIDATORS))

import jwt as pyjwt  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src import main  # noqa: E402

TEST_KID = "validators-test-key"
ISSUER = os.environ["VALIDATE_OIDC_ISSUER"].rstrip("/")
AUDIENCE = os.environ["VALIDATE_OIDC_AUDIENCE"]


@pytest.fixture(scope="session")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def other_rsa_key():
    """A second key used to sign tokens the JWKS must NOT accept."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(rsa_key):
    jwk = json.loads(pyjwt.algorithms.RSAAlgorithm.to_jwk(rsa_key.public_key()))
    jwk["kid"] = TEST_KID
    return {"keys": [jwk]}


def make_token(key, **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": "tester",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return pyjwt.encode(claims, key, algorithm="RS256", headers={"kid": TEST_KID})


@pytest.fixture()
def authed_client():
    """TestClient with the auth dependency replaced by a stub (non-auth tests)."""
    main.app.dependency_overrides[main.require_valid_token] = lambda: {"sub": "tester"}
    with TestClient(main.app) as client:
        yield client
    main.app.dependency_overrides.clear()
