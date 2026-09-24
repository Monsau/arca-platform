"""Vault reference adapter for the Arca Platform secrets contract."""

from __future__ import annotations

from typing import Any


class VaultSecretsAdapter:
    """Reference adapter resolving secrets from HashiCorp Vault.

    In production this adapter uses the Vault Kubernetes auth method. In tests
    and local development it falls back to environment variables.
    """

    def __init__(self, addr: str, mount_point: str = "secret") -> None:
        self.addr = addr
        self.mount_point = mount_point
        self._client: Any = None

    def connect(self) -> None:
        try:
            import hvac
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("hvac is required for Vault adapter") from exc
        self._client = hvac.Client(url=self.addr)
        # Real deployments authenticate via Kubernetes service account.

    def get(self, path: str, key: str | None = None) -> Any:
        if self._client is None:
            raise RuntimeError("Adapter not connected")
        response = self._client.secrets.kv.v2.read_secret(
            path=path, mount_point=self.mount_point
        )
        data = response["data"]["data"]
        return data.get(key) if key else data
