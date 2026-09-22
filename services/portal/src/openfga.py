"""OpenFGA client — ReBAC store for the Suite platform.

Reuses the ecosystem instance (arcaq-authorization). At startup the portal
ensures the 'arcasuite' store exists and the authorization model is written
once (schema 1.1: user / group with parent-member inheritance / module /
asset with viewer inheritance from its parent module).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

# Schema 1.1 authorization model, written once per store. Kept as literal
# type definitions (not parsed from DSL) so the wire format is exactly what
# the OpenFGA server expects, with full directly_related_user_types metadata:
# without metadata, direct tuples such as `user:test viewer module:packs`
# would be rejected at write time.
def _def(direct):
    return {"directly_related_user_types": direct}


USER_GROUP = [{"type": "user"}, {"type": "group", "relation": "member"}]

MODEL_TYPE_DEFINITIONS = [
    {"type": "user", "relations": {}},
    {
        "type": "group",
        "relations": {
            "parent": {"this": {}},
            "member": {
                "union": {
                    "child": [
                        {"this": {}},
                        {"tupleToUserset": {
                            "tupleset": {"object": "", "relation": "parent"},
                            "computedUserset": {"object": "", "relation": "member"}}},
                    ]
                }
            },
        },
        "metadata": {
            "relations": {
                "parent": _def([{"type": "group"}]),
                "member": _def(USER_GROUP),
            }
        },
    },
    {
        "type": "module",
        "relations": {
            "viewer": {"this": {}},
            "editor": {
                "union": {
                    "child": [
                        {"this": {}},
                        {"computedUserset": {"object": "", "relation": "viewer"}},
                    ]
                }
            },
            "owner": {
                "union": {
                    "child": [
                        {"this": {}},
                        {"computedUserset": {"object": "", "relation": "editor"}},
                    ]
                }
            },
        },
        "metadata": {
            "relations": {
                "viewer": _def(USER_GROUP),
                "editor": _def(USER_GROUP),
                "owner": _def([{"type": "user"}]),
            }
        },
    },
    {
        "type": "asset",
        "relations": {
            "parent": {"this": {}},
            "viewer": {
                "union": {
                    "child": [
                        {"this": {}},
                        {"tupleToUserset": {
                            "tupleset": {"object": "", "relation": "parent"},
                            "computedUserset": {"object": "", "relation": "viewer"}}},
                    ]
                }
            },
            "editor": {
                "union": {
                    "child": [
                        {"this": {}},
                        {"computedUserset": {"object": "", "relation": "viewer"}},
                    ]
                }
            },
            "owner": {
                "union": {
                    "child": [
                        {"this": {}},
                        {"computedUserset": {"object": "", "relation": "editor"}},
                    ]
                }
            },
        },
        "metadata": {
            "relations": {
                "parent": _def([{"type": "module"}]),
                "viewer": _def(USER_GROUP),
                "editor": _def(USER_GROUP),
                "owner": _def([{"type": "user"}]),
            }
        },
    },
]


class FGAError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(f"openfga {status}: {detail}")
        self.status = status
        self.detail = detail


class FGAClient:
    def __init__(self, base: str, store_name: str = "arcasuite"):
        self.base = base.rstrip("/")
        self.store_name = store_name
        self.store_id = ""
        self.model_id = ""

    # -- transport --------------------------------------------------------------
    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.base}{path}", method=method, data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                detail = json.loads(raw)
            except Exception:
                detail = raw[:200].decode(errors="replace")
            raise FGAError(e.code, detail)

    # -- bootstrap ----------------------------------------------------------------
    def ensure_store(self) -> None:
        stores = self._call("GET", "/stores").get("stores", [])
        for s in stores:
            if s.get("name") == self.store_name:
                self.store_id = s["id"]
                break
        if not self.store_id:
            self.store_id = self._call("POST", "/stores",
                                       {"name": self.store_name})["id"]
        self._ensure_model()

    def _ensure_model(self) -> None:
        models = self._call(
            "GET", f"/stores/{self.store_id}/authorization-models"
        ).get("authorization_models", [])
        if models:
            self.model_id = models[0]["id"]
            return
        self.model_id = self._call(
            "POST", f"/stores/{self.store_id}/authorization-models",
            {"schema_version": "1.1", "type_definitions": MODEL_TYPE_DEFINITIONS},
        )["authorization_model_id"]

    # -- tuples + checks ----------------------------------------------------------
    def write_tuple(self, user: str, relation: str, obj: str) -> None:
        self._call("POST", f"/stores/{self.store_id}/write", {
            "writes": {"tuple_keys": [
                {"user": user, "relation": relation, "object": obj}]}})

    def delete_tuple(self, user: str, relation: str, obj: str) -> None:
        self._call("POST", f"/stores/{self.store_id}/write", {
            "deletes": {"tuple_keys": [
                {"user": user, "relation": relation, "object": obj}]}})

    def check(self, user: str, relation: str, obj: str) -> bool:
        body = {"tuple_key": {"user": user, "relation": relation, "object": obj}}
        return bool(self._call(
            "POST", f"/stores/{self.store_id}/check", body).get("allowed"))

    def list_tuples(self, obj: str | None = None, user: str | None = None) -> list[dict]:
        body: dict = {"page_size": 100}
        if obj:
            body["object"] = obj
        if user:
            body["user"] = user
        return self._call(
            "POST", f"/stores/{self.store_id}/read", body).get("tuples", [])
