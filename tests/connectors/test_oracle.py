"""Tests for the Oracle connector."""

from __future__ import annotations

from adaptron.connectors.models import ConnectorConfig, CredentialConfig
from adaptron.connectors.oracle import OracleConnector
from adaptron.core.registry import global_registry


def test_registered_as_connector_oracle():
    """Verify that global_registry returns OracleConnector for connector/oracle."""
    cls = global_registry.get("connector", "oracle")
    assert cls is OracleConnector


def test_oracle_connector_builds_conn_str():
    """Verify _build_conn_str generates correct oracle+oracledb:// prefix."""
    config = ConnectorConfig(
        connector_type="oracle",
        host="ora.example.com",
        port=1522,
        database="ORCL",
        credentials=CredentialConfig(username="system", password="oracle123"),
    )
    conn_str = OracleConnector._build_conn_str(config)
    assert conn_str == "oracle+oracledb://system:oracle123@ora.example.com:1522/ORCL"

    # Test default port
    config_default = ConnectorConfig(
        connector_type="oracle",
        database="XE",
    )
    conn_str_default = OracleConnector._build_conn_str(config_default)
    assert conn_str_default == "oracle+oracledb://localhost:1521/XE"
