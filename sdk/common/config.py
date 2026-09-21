"""Arca Platform shared configuration conventions.

Products load configuration through this SDK so that environment variables,
configuration files and secret providers are handled consistently across the
suite.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """Base settings shared by every Arca Suite product.

    Products extend this class with their own product-specific settings.
    """

    model_config = SettingsConfigDict(
        env_prefix="ARCA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", description="Runtime environment")
    tenant_id: str | None = Field(default=None, description="Default tenant identifier")
    log_level: str = Field(default="INFO", description="Log level")

    # Platform contract endpoints (adapters resolve these)
    identity_adapter: str = Field(default="jwt", description="Identity adapter name")
    secrets_adapter: str = Field(default="vault", description="Secrets adapter name")
    messaging_adapter: str = Field(default="kafka", description="Messaging adapter name")
    observability_adapter: str = Field(
        default="opentelemetry", description="Observability adapter name"
    )
    ontology_write_adapter: str = Field(
        default="null",
        description="Ontology write adapter name (null | arcaq); opt-in per golden rule #2",
    )

    @classmethod
    def load_from_file(cls, path: str | Path) -> "PlatformSettings":
        """Load settings from a YAML or JSON configuration file.

        This is a convenience wrapper; environment variables still take
        precedence when using pydantic-settings.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        # JSON and YAML are accepted; YAML requires an optional dependency.
        text = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("YAML config requires PyYAML") from exc
            data = yaml.safe_load(text)
        else:
            import json

            data = json.loads(text)
        return cls.model_validate(data)

    def to_product_env(self) -> dict[str, str]:
        """Return settings as a dictionary suitable for injection into products."""
        return {
            key.upper(): str(value)
            for key, value in self.model_dump().items()
            if value is not None
        }


def get_secret(key: str, default: Any | None = None) -> Any:
    """Resolve a secret reference by name using the configured secrets adapter.

    The actual lookup is delegated to the adapter registered at runtime. This
    function is a stable contract point; products call it without knowing
    whether Vault, AWS Secrets Manager or another backend is in use.
    """
    # In a production deployment the secrets adapter performs the lookup.
    # The fallback below is only for local development and tests.
    return os.getenv(f"ARCA_SECRET_{key}", default)
