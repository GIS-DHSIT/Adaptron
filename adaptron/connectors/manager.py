"""Connection manager with YAML-based profile storage."""
from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from adaptron.connectors.models import ConnectorConfig, CredentialConfig


class ConnectionManager:
    """Saves, loads, and removes connection profiles from a YAML file."""

    def __init__(self, profiles_path: Path | None = None) -> None:
        if profiles_path is None:
            env_path = os.environ.get("ADAPTRON_CONNECTIONS_FILE")
            if env_path:
                profiles_path = Path(env_path)
            else:
                profiles_path = Path.home() / ".adaptron" / "connections.yaml"
        self._path = profiles_path

    async def connect(self, profile_name: str) -> Any:
        """Load a profile and connect using the appropriate connector."""
        config = self.load_profile(profile_name)
        return await self.connect_with_config(config)

    async def connect_with_config(self, config: ConnectorConfig) -> Any:
        """Create and connect a connector from a ConnectorConfig directly."""
        from adaptron.core.registry import global_registry

        connector_cls = global_registry.get("connector", config.connector_type)
        connector = connector_cls()
        await connector.connect(config)
        return connector

    def _read_profiles(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        return data.get("profiles", {})

    def _write_profiles(self, profiles: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.dump({"profiles": profiles}, default_flow_style=False),
            encoding="utf-8",
        )

    def save_profile(self, name: str, config: ConnectorConfig) -> None:
        """Serialize a ConnectorConfig to YAML.

        Passwords are never stored directly; only credential references
        (env_var, aws_secret, azure_vault) are persisted.
        """
        profiles = self._read_profiles()
        data = asdict(config)
        # Strip None values for cleanliness
        data = {k: v for k, v in data.items() if v is not None}
        # Remove direct passwords from credentials
        if "credentials" in data and data["credentials"]:
            creds = data["credentials"]
            creds.pop("password", None)
            creds.pop("username", None)
            creds = {k: v for k, v in creds.items() if v is not None}
            if creds:
                data["credentials"] = creds
            else:
                del data["credentials"]
        # Remove empty options dict
        if "options" in data and not data["options"]:
            del data["options"]
        profiles[name] = data
        self._write_profiles(profiles)

    def load_profile(self, name: str) -> ConnectorConfig:
        """Deserialize a profile from YAML. Raises KeyError if not found."""
        profiles = self._read_profiles()
        if name not in profiles:
            raise KeyError(f"Profile '{name}' not found")
        data = profiles[name]
        creds = data.pop("credentials", None)
        credential_config = CredentialConfig(**creds) if creds else None
        return ConnectorConfig(credentials=credential_config, **data)

    def remove_profile(self, name: str) -> None:
        """Remove a profile from the YAML file."""
        profiles = self._read_profiles()
        profiles.pop(name, None)
        self._write_profiles(profiles)

    def list_profiles(self) -> list[str]:
        """Return a list of all profile names."""
        return list(self._read_profiles().keys())
