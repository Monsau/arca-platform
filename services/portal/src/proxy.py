"""Reverse proxy from the portal shell to suite module services.

Every request under /m/<module>/... is forwarded to the module's in-cluster
service with the caller's Keycloak access token attached as a Bearer token,
so modules observe one consistent identity regardless of entry point.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import Request
from fastapi.responses import Response, StreamingResponse

from .config import Module

logger = logging.getLogger(__name__)

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class ModuleProxy:
    def __init__(self, public_base_url: str = "") -> None:
        # No http2: module backends are plain HTTP/1.1 uvicorns.
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0))
        self._public_base = public_base_url.rstrip("/")

    def _rewrite_location(self, location: str, module: Module, base: str) -> str:
        """Map upstream redirect targets back to the portal mount point.

        Modules build absolute redirect URLs from the request Host (the
        in-cluster service name), and relative ones stay inside their own
        mount path; both must target /m/<key> on the portal origin.
        """
        if location.startswith(base):
            if not self._public_base:
                return location
            return f"{self._public_base}/m/{module.key}{location[len(base):]}"
        if location.startswith("/") and not location.startswith("//"):
            return f"/m/{module.key}{location}"
        return location

    async def forward(self, module: Module, rest: str, request: Request, token: str) -> Response:
        base = module.service.rstrip("/")
        # rest already includes the ui_base prefix stripped by the caller.
        url = f"{base}{rest}"
        headers = {
            k.lower(): v
            for k, v in request.headers.items()
            if k.lower() not in _HOP_BY_HOP and k.lower() not in ("host", "cookie")
        }
        headers["authorization"] = f"Bearer {token}"
        headers["x-arca-portal"] = "1"
        body = await request.body()
        try:
            upstream = await self._client.request(
                request.method, url, params=request.query_params, headers=headers, content=body
            )
        except httpx.TransportError as exc:
            logger.warning("proxy to %s failed: %s", module.key, exc)
            return _module_error(module, "unreachable", exc)

        resp_headers = {
            k: v
            for k, v in upstream.headers.items()
            if k.lower() not in _HOP_BY_HOP and k.lower() not in ("content-length", "content-encoding")
        }
        location = upstream.headers.get("location")
        if location:
            resp_headers["location"] = self._rewrite_location(location, module, base)
        return StreamingResponse(
            upstream.aiter_raw(),
            status_code=upstream.status_code,
            headers=resp_headers,
            background=upstream.aclose,
        )


def _module_error(module: Module, reason: str, exc: Exception | None = None) -> Response:
    """Honest module failure page — no fabricated status, no mock content."""
    detail = f"{type(exc).__name__}: {exc}" if exc else reason
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{{font-family:system-ui,sans-serif;background:#111113;color:#a1a1aa;display:flex;
       align-items:center;justify-content:center;height:100vh;margin:0}}
  .card{{background:#18181b;border:1px solid rgba(255,255,255,.06);border-radius:16px;
        padding:32px 40px;text-align:center;max-width:420px}}
  h2{{color:#fafafa;font-size:17px;margin:0 0 8px}}
  p{{font-size:13px;margin:0 0 4px}}
  code{{font-size:11px;color:#71717a}}
</style></head><body><div class="card">
  <h2>Module unavailable — {module.name}</h2>
  <p>The module did not answer. Its real status is reported below; nothing is simulated.</p>
  <code>{module.service}{reason}: {detail}</code>
</div></body></html>"""
    return Response(html, status_code=502, media_type="text/html")
