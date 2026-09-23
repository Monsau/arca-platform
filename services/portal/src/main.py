"""Arca Suite Portal — FastAPI application.

Routes:
  /                    shell overview (module health from live probes)
  /m/<key>/<path>      authenticated reverse proxy to a suite module
  /auth/login|callback|logout   Keycloak OIDC flow
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import AuthError, OIDCClient, SessionStore
from .config import Settings, load_ecosystem, load_modules
from .proxy import ModuleProxy

APP_VERSION = "0.3.4"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

settings = Settings()
modules = {m.key: m for m in load_modules()}
store = SessionStore(settings.redis_url, settings.session_ttl_seconds)
auth = OIDCClient(settings, store)
proxy = ModuleProxy(settings.public_base_url)
probe_client = httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0))

app = FastAPI(title="Arca Suite Portal", version=APP_VERSION, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Transient OIDC state (single-process; login handled by one replica behind
# the shell's single-replica deployment — see portal.md operations note).
_pending_states: set[str] = set()

# Sister products of the suite: same realm, same users, full-page navigation
# (they own their UI and auth session; the portal only links out). Wiring is
# config-driven via PORTAL_ECOSYSTEM — see config.load_ecosystem.
ECOSYSTEM = [link.__dict__ for link in load_ecosystem()]


def _session(request: Request) -> dict | None:
    return auth.load_session(request.cookies.get(settings.session_cookie))


def _session_roles(session: dict) -> set[str]:
    """Roles carried by the session, from the ID-token `roles` claim (realm
    roles mapper) plus the standard realm_access block."""
    claims = session.get("claims", {}) or {}
    raw = claims.get("roles") or []
    if isinstance(raw, str):
        raw = [r.strip() for r in raw.split(",") if r.strip()]
    realm = (claims.get("realm_access") or {}).get("roles", []) or []
    return set(raw) | set(realm)


def _is_platform_member(session: dict) -> bool:
    """The platform is squad-gated: members of any squad (marker role) and
    the suite-wide admin pass; every other authenticated account is refused."""
    roles = _session_roles(session)
    return "admin" in roles or "squad-member" in roles


def _forbidden(request: Request, session: dict) -> Response:
    return templates.TemplateResponse(
        request,
        "forbidden.html",
        {
            "user": session.get("claims", {}),
            "modules": [dict(key=m.key, name=m.name, icon=m.icon, description=m.description) for m in modules.values()],
            "ecosystem": ECOSYSTEM,
            "hide_nav": True,
        },
        status_code=403,
    )


def _require_session(request: Request) -> dict:
    session = _session(request)
    if not session:
        raise HTTPException(status_code=401, detail="authentication required")
    return session


def _is_navigation(request: Request) -> bool:
    """True when the request is a page navigation (top level or iframe).

    Fetch/XHR API calls from module UIs are left as 401 JSON so the portal
    owns the auth experience; only document navigations are bounced to the
    centralized Keycloak login.
    """
    dest = request.headers.get("sec-fetch-dest", "")
    if dest in ("document", "iframe"):
        return True
    accept = request.headers.get("accept", "")
    return request.method == "GET" and "text/html" in accept


def _auth_expired(request: Request) -> Response:
    """Centralized auth handling (platform-owned): navigations bounce to the
    Keycloak login flow; API calls receive an honest 401."""
    if _is_navigation(request):
        return RedirectResponse("/auth/login", status_code=303)
    raise HTTPException(status_code=401, detail="authentication required")


def _require_admin(request: Request) -> dict:
    """Dependency: access governance is an admin-only surface."""
    session = _session(request)
    if not session:
        raise HTTPException(status_code=401, detail="authentication required")
    if "admin" not in _session_roles(session):
        raise HTTPException(status_code=403, detail="admin role required")
    return session


# Access governance (OpenMetadata-style): roles, group hierarchy, user
# grants, policies and ReBAC tuples, backed by the Keycloak service-account
# client and the shared OpenFGA instance (ecosystem reuse).
kc_admin = None
fga_client = None
if settings.kc_admin_base and settings.kc_admin_client_id and settings.kc_admin_client_secret:
    _realm = settings.oidc_issuer.rstrip("/").rsplit("/realms/", 1)[-1]
    from .access import KCAdmin, build_router

    kc_admin = KCAdmin(
        base=settings.kc_admin_base.rstrip("/"),
        realm=_realm,
        client_id=settings.kc_admin_client_id,
        client_secret=settings.kc_admin_client_secret,
    )
    if settings.openfga_url:
        from .openfga import FGAClient

        # Bootstrap is best-effort at startup: if OpenFGA is briefly
        # unreachable the app still boots and the routes answer 503 until
        # PORTAL_OPENFGA_URL is reachable and the store is ensured.
        try:
            fga_client = FGAClient(settings.openfga_url)
            fga_client.ensure_store()
            logger.info("openfga store ready: %s", fga_client.store_id)
        except Exception as exc:  # noqa: BLE001 — boot must not fail on authz
            logger.error("openfga bootstrap failed, authz routes disabled: %s", exc)
            fga_client = None
    app.include_router(
        build_router(kc_admin, fga_client), dependencies=[Depends(_require_admin)])


@app.get("/api/me")
async def me(request: Request) -> dict:
    """The caller's own session claims — used to prove rights propagation."""
    session = _session(request)
    if not session:
        raise HTTPException(status_code=401, detail="authentication required")
    claims = session.get("claims", {}) or {}
    return {
        "sub": claims.get("sub"),
        "username": claims.get("preferred_username"),
        "roles": sorted(_session_roles(session)),
    }


@app.get("/access", response_class=HTMLResponse)
async def access_page(request: Request) -> Response:
    session = _require_admin(request)
    claims = session.get("claims", {}) or {}
    return templates.TemplateResponse(
        request,
        "access.html",
        {
            "user": claims,
            "modules": [dict(key=m.key, name=m.name, icon=m.icon, description=m.description) for m in modules.values()],
            "ecosystem": ECOSYSTEM,
            "active": "access",
        },
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "healthy", "oidc_configured": settings.configured}


@app.get("/auth/login")
async def login(request: Request) -> Response:
    if not settings.configured:
        return HTMLResponse(_not_configured(), status_code=500)
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return RedirectResponse(auth.authorize_redirect(state))


@app.get("/auth/callback")
async def callback(request: Request, state: str = "", code: str = "") -> Response:
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="invalid state")
    _pending_states.discard(state)
    if not code:
        raise HTTPException(status_code=400, detail="missing code")
    try:
        result = await auth.exchange_code(code)
    except AuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    sid = auth.create_session(result["tokens"], result["claims"])
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        settings.session_cookie,
        auth.encode_cookie(sid),
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return resp


@app.get("/auth/logout")
async def logout(request: Request) -> Response:
    id_token_hint = auth.destroy_session(request.cookies.get(settings.session_cookie))
    params = {"client_id": settings.oidc_client_id}
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    if settings.public_base_url:
        params["post_logout_redirect_uri"] = settings.public_base_url
    resp = RedirectResponse(f"{settings.end_session_url}?{httpx.QueryParams(params)}")
    resp.delete_cookie(settings.session_cookie)
    return resp


@app.get("/", response_class=HTMLResponse)
async def overview(request: Request) -> Response:
    session = _session(request)
    if not session:
        return RedirectResponse("/auth/login")
    if not _is_platform_member(session):
        return _forbidden(request, session)
    claims = session.get("claims", {})
    statuses = await _probe_modules()
    return templates.TemplateResponse(
        request,
        "overview.html",
        {
            "user": claims,
            "modules": [dict(key=m.key, name=m.name, icon=m.icon, description=m.description) for m in modules.values()],
            "statuses": statuses,
            "ecosystem": ECOSYSTEM,
        },
    )


@app.get("/api/statuses")
async def module_statuses(request: Request) -> dict:
    """Fresh module health as JSON — powers the overview auto-refresh
    without a full page reload. Session required, same rule as pages."""
    session = _require_session(request)
    if not _is_platform_member(session):
        raise HTTPException(status_code=403, detail="squad membership required")
    statuses = await _probe_modules()
    return {
        "statuses": statuses,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.api_route("/m/{key}/{rest:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def module_proxy(key: str, rest: str, request: Request) -> Response:
    session = _session(request)
    if not session:
        return _auth_expired(request)
    # Squad gate, same rule as pages and /api/statuses: the platform and all
    # its modules are reserved to squad members and suite admins. Without
    # this, any authenticated realm account could reach module APIs directly
    # even though the portal UI refuses them.
    if not _is_platform_member(session):
        return _forbidden(request, session)
    # Security by design: always forward the session's SSO access token
    # (refreshed when close to expiry). No token, no call — modules reject
    # anonymous requests, and so does the portal.
    token = await auth.ensure_fresh_token(request.cookies.get(settings.session_cookie))
    if not token:
        return _auth_expired(request)
    module = modules.get(key)
    if not module:
        raise HTTPException(status_code=404, detail="unknown module")
    # Verbatim contract: /m/<key>/<path> is forwarded to the module service
    # as /<path>, unchanged. Module UIs mounted under the portal must emit
    # prefix-aware URLs: relative assets, and API calls against
    # /m/<key>/api/... (see portal.md). Relative redirect Locations from the
    # module are rewritten back under /m/<key> by the proxy.
    path = "/" + rest if rest else "/"
    return await proxy.forward(module, path, request, token=token,
                               navigation=_is_navigation(request))


async def _probe_modules() -> dict[str, dict]:
    """Live health of every module — real probes, honest failures."""
    statuses: dict[str, dict] = {}

    async def probe(key: str, service: str, health: str) -> None:
        url = f"{service.rstrip('/')}{health}"
        try:
            resp = await probe_client.get(url)
            statuses[key] = {"ok": resp.status_code < 500, "status": resp.status_code}
        except httpx.TransportError as exc:
            statuses[key] = {"ok": False, "status": str(exc)[:60]}

    import asyncio

    await asyncio.gather(*(probe(m.key, m.service, m.health) for m in modules.values()))
    return statuses


def _not_configured() -> str:
    return (
        "<h1>Portal OIDC is not configured</h1>"
        "<p>Set PORTAL_OIDC_ISSUER, PORTAL_OIDC_CLIENT_SECRET and "
        "PORTAL_OIDC_REDIRECT_URI.</p>"
    )


@app.get("/module/{key}", response_class=HTMLResponse)
async def module_frame(key: str, request: Request) -> Response:
    """Shell page hosting one module in a fluid full-size frame."""
    session = _session(request)
    if not session:
        return RedirectResponse("/auth/login")
    if not _is_platform_member(session):
        return _forbidden(request, session)
    module = modules.get(key)
    if not module:
        raise HTTPException(status_code=404, detail="unknown module")
    claims = session.get("claims", {})
    return templates.TemplateResponse(
        request,
        "module.html",
        {
            "user": claims,
            "active": key,
            "module": module,
            "ecosystem": ECOSYSTEM,
            "modules": [dict(key=m.key, name=m.name, icon=m.icon, description=m.description) for m in modules.values()],
        },
    )
