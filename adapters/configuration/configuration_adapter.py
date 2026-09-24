"""Reference configuration adapter for the Arca Platform configuration contract.

File-backed (YAML or JSON) loading of the platform configuration document
defined by `contracts/configuration/`. Environment variables still take
precedence through `PlatformSettings`; this adapter is the file side of
that convention.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigurationAdapter(Protocol):
    """Neutral interface for loading platform configuration."""

    def load(self) -> dict[str, Any]:
        ...

    def get(self, key: str, default: Any | None = None) -> Any:
        ...


class FileConfigurationAdapter:
    """Loads the platform configuration document from a YAML or JSON file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._document: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        if self._document is not None:
            return self._document
        if not self.path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {self.path}")
        text = self.path.read_text(encoding="utf-8")
        if self.path.suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("YAML config requires PyYAML") from exc
            document = yaml.safe_load(text)
        else:
            document = json.loads(text)
        if not isinstance(document, dict):
            raise ValueError(f"Configuration document must be an object: {self.path}")
        self._document = document
        return self._document

    def get(self, key: str, default: Any | None = None) -> Any:
        """Dotted-key lookup, e.g. ``adapters.secrets``."""
        current: Any = self.load()
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def reload(self) -> dict[str, Any]:
        """Drop the cached document and read the file again."""
        self._document = None
        return self.load()
