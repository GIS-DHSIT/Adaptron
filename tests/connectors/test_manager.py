"""Tests for ConnectionManager."""
from pathlib import Path

import pytest

from adaptron.connectors.manager import ConnectionManager
from adaptron.connectors.models import ConnectorConfig, CredentialConfig


def test_save_and_load_profile(tmp_path: Path) -> None:
    mgr = ConnectionManager(profiles_path=tmp_path / "connections.yaml")
    config = ConnectorConfig(
        connector_type="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
        credentials=CredentialConfig(env_var="DB_URL"),
    )
    mgr.save_profile("my-db", config)
    names = mgr.list_profiles()
    assert "my-db" in names


def test_load_profile(tmp_path: Path) -> None:
    mgr = ConnectionManager(profiles_path=tmp_path / "connections.yaml")
    config = ConnectorConfig(
        connector_type="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
        credentials=CredentialConfig(env_var="DB_URL"),
    )
    mgr.save_profile("my-db", config)
    loaded = mgr.load_profile("my-db")
    assert loaded.connector_type == "postgresql"
    assert loaded.host == "localhost"
    assert loaded.port == 5432
    assert loaded.database == "mydb"
    assert loaded.credentials is not None
    assert loaded.credentials.env_var == "DB_URL"


def test_load_missing_profile_raises(tmp_path: Path) -> None:
    mgr = ConnectionManager(profiles_path=tmp_path / "connections.yaml")
    with pytest.raises(KeyError, match="not found"):
        mgr.load_profile("nonexistent")


def test_remove_profile(tmp_path: Path) -> None:
    mgr = ConnectionManager(profiles_path=tmp_path / "connections.yaml")
    config = ConnectorConfig(
        connector_type="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
        credentials=CredentialConfig(env_var="DB_URL"),
    )
    mgr.save_profile("my-db", config)
    assert "my-db" in mgr.list_profiles()
    mgr.remove_profile("my-db")
    assert "my-db" not in mgr.list_profiles()


def test_empty_profiles(tmp_path: Path) -> None:
    mgr = ConnectionManager(profiles_path=tmp_path / "connections.yaml")
    assert mgr.list_profiles() == []
