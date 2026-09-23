"""Arca Validate — FastAPI application.

Shared declarative contract validation for Suite artifacts (Turtle ontologies,
SHACL contracts, OOC manifests, workflow definitions). WSDL/XSD-inspired
quality gates applied to the Suite's own formats: explicit checks, explicit
violations, nothing validated unproven.

Security by design: every /api/v1/validate call carries the caller's Keycloak
SSO token (RS256) which is fully verified before any validation work happens.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from .auth import AuthRejected, TokenValidator
from .config import Settings, get_settings
from .gates.manifest import validate_ooc_manifest
from .gates.ontology import validate_ontology_ttl
from .gates.workflow import validate_workflow_yaml

settings: Settings = get_settings()
token_validator = TokenValidator(settings)

SUPPORTED_ARTIFACT_KINDS = ("ontology_ttl", "ooc_manifest", "workflow_yaml")

app = FastAPI(title="Arca Validate", version="1.0.0")


class ValidateRequest(BaseModel):
    artifact_kind: str
    content: str
    content_format: Optional[Literal["yaml", "json"]] = None
    profile: Optional[str] = None


class CheckOut(BaseModel):
    gate: str
    passed: bool
    severity: Literal["violation", "warning"]
    message: str


class ValidateResponse(BaseModel):
    valid: bool
    artifact_kind: str
    checks: list[CheckOut]
    normalized: Optional[str]
    detail: str


async def require_valid_token(
    authorization: Annotated[Optional[str], Header()] = None,
) -> dict:
    """FastAPI dependency: reject the request before any validation work
    unless a fully verified SSO token is present."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization: Bearer token",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
        )
    try:
        return await token_validator.validate(token.strip())
    except AuthRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid token: {exc}",
        ) from exc
    except Exception as exc:  # noqa: BLE001 — JWKS endpoint down etc: fail closed
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"token could not be verified: {exc}",
        ) from exc


@app.get("/healthz")
async def healthz() -> str:
    """Plain liveness probe for k8s — no auth."""
    return "ok"


@app.post("/api/v1/validate", response_model=ValidateResponse)
async def validate(
    request: ValidateRequest,
    _claims: Annotated[dict, Depends(require_valid_token)],
) -> ValidateResponse:
    """Validate a Suite artifact against its declarative contracts."""
    if request.artifact_kind not in SUPPORTED_ARTIFACT_KINDS:
        raise HTTPException(
            status_code=422,  # unprocessable content
            detail={
                "message": f"unknown artifact_kind: {request.artifact_kind!r}",
                "supported_artifact_kinds": list(SUPPORTED_ARTIFACT_KINDS),
            },
        )

    if request.artifact_kind == "ontology_ttl":
        report = validate_ontology_ttl(request.content, settings.shapes_dir)
    elif request.artifact_kind == "ooc_manifest":
        report = validate_ooc_manifest(request.content, request.content_format)
    else:  # workflow_yaml
        report = validate_workflow_yaml(request.content)

    return ValidateResponse(
        valid=report.valid,
        artifact_kind=request.artifact_kind,
        checks=[CheckOut(**c.as_dict()) for c in report.checks],
        normalized=report.normalized,
        detail=report.detail,
    )
