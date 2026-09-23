"""Access governance — roles / groups (hierarchy) / memberships / policies / ReBAC.

OpenMetadata-style administration surface, backed by Keycloak Admin REST
(roles, groups, group-role mappings, memberships), the platform policy store
(role -> module/action grants) in Postgres, and the shared OpenFGA instance
(arcaq-authorization) for relation-based access control: direct grants,
group-membership grants and parent-inheritance between assets and modules.

The portal talks to Keycloak with a dedicated service-account client
(PORTAL_KC_ADMIN_CLIENT_ID / _SECRET) holding manage-realm + manage-users.
Every route is wired in main.py behind the admin gate.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException, Request

from .openfga import MODEL_TYPE_DEFINITIONS

POLICY_DSN = os.environ.get("PORTAL_POLICY_DB_DSN", "").strip()


# ---------------------------------------------------------------------------
# Keycloak admin client (service account, token cached until near expiry)
# ---------------------------------------------------------------------------
@dataclass
class KCAdmin:
    base: str           # in-cluster base, e.g. http://keycloak.auth.svc.cluster.local:8080
    realm: str
    client_id: str
    client_secret: str
    _token: str = ""
    _exp: float = 0.0

    def _url(self, path: str) -> str:
        return f"{self.base}/admin/realms/{self.realm}{path}"

    def _token_url(self) -> str:
        return (f"{self.base}/realms/{self.realm}/protocol/openid-connect/token")

    def _refresh(self) -> None:
        if self._token and time.time() < self._exp - 30:
            return
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }).encode()
        with urllib.request.urlopen(
                urllib.request.Request(
                    self._token_url(), data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}),
                timeout=15) as r:
            payload = json.loads(r.read())
        self._token = payload["access_token"]
        self._exp = time.time() + float(payload.get("expires_in", 300))

    def call(self, method: str, path: str, body: dict | None = None):
        self._refresh()
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self._url(path), method=method, data=data,
            headers={"Authorization": f"Bearer {self._token}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                detail = json.loads(raw)
            except Exception:
                detail = {"error": raw[:200].decode(errors="replace")}
            raise HTTPException(status_code=e.code, detail=detail)

    # -- roles ----------------------------------------------------------------
    def list_roles(self) -> list[str]:
        _, roles = self.call("GET", "/roles")
        return sorted(r["name"] for r in roles)

    def create_role(self, name: str) -> None:
        self.call("POST", "/roles", {"name": name})

    def delete_role(self, name: str) -> None:
        self.call("DELETE", f"/roles/{urllib.parse.quote(name, safe='')}")

    # -- groups ---------------------------------------------------------------
    def list_groups(self) -> list[dict]:
        """Full group list with parent links, via the dedicated children
        endpoint (this Keycloak returns subGroupCount but an empty subGroups
        list on both /groups and /groups/{id} representations)."""
        _, tree = self.call("GET", "/groups?max=1000")
        flat: list[dict] = []

        def walk(node, parent):
            flat.append({"name": node["name"], "parent": parent,
                         "id": node.get("id")})
            _, children = self.call(
                "GET", f"/groups/{node['id']}/children?max=1000")
            for sub in children:
                walk(sub, node["name"])

        for g in tree:
            walk(g, None)
        return flat

    def _group_id(self, name: str) -> str:
        """Resolve a group id by exact name, walking search-result subtrees
        (children are nested under their parent, never top-level results)."""
        _, found = self.call(
            "GET", f"/groups?search={urllib.parse.quote(name, safe='')}")
        stack = list(found)
        while stack:
            node = stack.pop()
            if node["name"] == name:
                return node["id"]
            stack.extend(node.get("subGroups") or [])
        raise HTTPException(status_code=404, detail=f"group not found: {name}")

    def create_group(self, name: str, parent: str | None = None) -> None:
        body = {"name": name}
        if parent:
            pid = self._group_id(parent)
            self.call("POST", f"/groups/{pid}/children", body)
        else:
            self.call("POST", "/groups", body)

    def delete_group(self, name: str) -> None:
        self.call("DELETE", f"/groups/{self._group_id(name)}")

    # -- members ---------------------------------------------------------------
    def list_members(self, group: str) -> list[dict]:
        gid = self._group_id(group)
        _, users = self.call("GET", f"/groups/{gid}/members")
        return [{"username": u.get("username"), "id": u.get("id")} for u in users]

    def add_member(self, group: str, username: str) -> None:
        gid = self._group_id(group)
        _, users = self.call("GET", f"/users?username={urllib.parse.quote(username, safe='')}")
        user = next((u for u in users if u.get("username") == username), None)
        if not user:
            raise HTTPException(status_code=404, detail=f"user not found: {username}")
        self.call("PUT", f"/users/{user['id']}/groups/{gid}")

    # -- group role mappings (kit) ---------------------------------------------
    def list_group_roles(self, group: str) -> list[str]:
        gid = self._group_id(group)
        _, mappings = self.call("GET", f"/groups/{gid}/role-mappings/realm")
        return sorted(r["name"] for r in mappings)

    def add_group_role(self, group: str, role: str) -> None:
        gid = self._group_id(group)
        _, roles = self.call("GET", "/roles")
        target = next((r for r in roles if r["name"] == role), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"role not found: {role}")
        self.call("POST", f"/groups/{gid}/role-mappings/realm", [target])

    def remove_group_role(self, group: str, role: str) -> None:
        gid = self._group_id(group)
        _, roles = self.call("GET", "/roles")
        target = next((r for r in roles if r["name"] == role), None)
        if not target:
            raise HTTPException(status_code=404, detail=f"role not found: {role}")
        self.call("DELETE", f"/groups/{gid}/role-mappings/realm", [target])


# ---------------------------------------------------------------------------
# Policies: role -> grants, stored in Postgres (psycopg, sync via to_thread)
# ---------------------------------------------------------------------------
_POLICY_TABLE = """
CREATE TABLE IF NOT EXISTS access_policies (
    name TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    grants JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def _policy_conn():
    import psycopg
    conn = psycopg.connect(POLICY_DSN)
    conn.execute(_POLICY_TABLE)
    conn.commit()
    return conn


async def list_policies() -> list[dict]:
    def _q():
        with _policy_conn() as c:
            rows = c.execute(
                "SELECT name, role, grants::text FROM access_policies ORDER BY name"
            ).fetchall()
            return [{"name": n, "role": r, "grants": json.loads(g)} for n, r, g in rows]

    return await asyncio.to_thread(_q)


async def save_policy(name: str, role: str, grants: list[dict]) -> None:
    def _q():
        with _policy_conn() as c:
            c.execute(
                "INSERT INTO access_policies (name, role, grants) VALUES (%s, %s, %s::jsonb) "
                "ON CONFLICT (name) DO UPDATE SET role = EXCLUDED.role, grants = EXCLUDED.grants",
                (name, role, json.dumps(grants)))
            c.commit()

    await asyncio.to_thread(_q)


async def delete_policy(name: str) -> None:
    def _q():
        with _policy_conn() as c:
            c.execute("DELETE FROM access_policies WHERE name = %s", (name,))
            c.commit()

    await asyncio.to_thread(_q)


# ---------------------------------------------------------------------------
# Router — wired in main.py behind the admin gate
# ---------------------------------------------------------------------------
def build_router(kc: KCAdmin, fga=None) -> APIRouter:
    """Governance routes. `fga` is an FGAClient; ReBAC routes answer 503 when
    PORTAL_OPENFGA_URL is not configured, so governance degrades gracefully."""
    router = APIRouter(prefix="/admin/access")

    @router.get("/roles")
    def roles():
        return {"roles": kc.list_roles()}

    @router.post("/roles", status_code=201)
    def create_role(body: dict):
        name = (body or {}).get("name", "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="name is required")
        kc.create_role(name)
        return {"name": name}

    @router.delete("/roles/{name}", status_code=204)
    def delete_role(name: str):
        kc.delete_role(name)

    @router.get("/groups")
    def groups():
        return {"groups": kc.list_groups()}

    @router.post("/groups", status_code=201)
    def create_group(body: dict):
        name = (body or {}).get("name", "").strip()
        parent = (body or {}).get("parent", "").strip() or None
        if not name:
            raise HTTPException(status_code=422, detail="name is required")
        kc.create_group(name, parent)
        return {"name": name, "parent": parent}

    @router.delete("/groups/{name}", status_code=204)
    def delete_group(name: str):
        kc.delete_group(name)

    @router.get("/groups/{name}/members")
    def members(name: str):
        return {"members": kc.list_members(name)}

    @router.post("/groups/{name}/members", status_code=201)
    def add_member(name: str, body: dict):
        username = (body or {}).get("username", "").strip()
        if not username:
            raise HTTPException(status_code=422, detail="username is required")
        kc.add_member(name, username)
        return {"group": name, "username": username}

    @router.get("/groups/{name}/roles")
    def group_roles(name: str):
        return {"roles": kc.list_group_roles(name)}

    @router.post("/groups/{name}/roles", status_code=201)
    def add_group_role(name: str, body: dict):
        role = (body or {}).get("name", "").strip()
        if not role:
            raise HTTPException(status_code=422, detail="name is required")
        kc.add_group_role(name, role)
        return {"group": name, "role": role}

    @router.get("/policies")
    async def policies():
        return {"policies": await list_policies()}

    @router.post("/policies", status_code=201)
    async def create_policy(body: dict):
        if not POLICY_DSN:
            raise HTTPException(status_code=503, detail="policy store not configured")
        name = (body or {}).get("name", "").strip()
        role = (body or {}).get("role", "").strip()
        grants = (body or {}).get("grants") or []
        if not name or not role or not grants:
            raise HTTPException(status_code=422, detail="name, role and grants are required")
        await save_policy(name, role, grants)
        return {"name": name, "role": role, "grants": grants}

    @router.delete("/policies/{name}", status_code=204)
    async def remove_policy(name: str):
        if not POLICY_DSN:
            raise HTTPException(status_code=503, detail="policy store not configured")
        await delete_policy(name)

    # -- ReBAC (OpenFGA): fine-grained relation tuples on modules and assets --
    def _require_fga():
        if fga is None:
            raise HTTPException(status_code=503, detail="openfga not configured")
        return fga

    @router.get("/authz/model")
    def authz_model():
        client = _require_fga()
        return {"store": client.store_name, "store_id": client.store_id,
                "model_id": client.model_id, "schema": "1.1",
                "types": [t["type"] for t in MODEL_TYPE_DEFINITIONS]}

    @router.get("/authz/tuples")
    def authz_tuples(object: str = "", user: str = ""):
        client = _require_fga()
        tuples = client.list_tuples(obj=object or None, user=user or None)
        return {"tuples": [
            {"user": t["key"]["user"], "relation": t["key"]["relation"],
             "object": t["key"]["object"]} for t in tuples]}

    @router.post("/authz/tuples", status_code=201)
    def authz_grant(body: dict):
        client = _require_fga()
        user = (body or {}).get("user", "").strip()
        relation = (body or {}).get("relation", "").strip()
        obj = (body or {}).get("object", "").strip()
        if not user or not relation or not obj:
            raise HTTPException(
                status_code=422, detail="user, relation and object are required")
        client.write_tuple(user, relation, obj)
        return {"user": user, "relation": relation, "object": obj}

    @router.delete("/authz/tuples", status_code=204)
    def authz_revoke(body: dict):
        client = _require_fga()
        user = (body or {}).get("user", "").strip()
        relation = (body or {}).get("relation", "").strip()
        obj = (body or {}).get("object", "").strip()
        if not user or not relation or not obj:
            raise HTTPException(
                status_code=422, detail="user, relation and object are required")
        client.delete_tuple(user, relation, obj)

    @router.post("/authz/check")
    def authz_check(body: dict):
        client = _require_fga()
        user = (body or {}).get("user", "").strip()
        relation = (body or {}).get("relation", "").strip()
        obj = (body or {}).get("object", "").strip()
        if not user or not relation or not obj:
            raise HTTPException(
                status_code=422, detail="user, relation and object are required")
        return {"allowed": client.check(user, relation, obj)}

    return router
