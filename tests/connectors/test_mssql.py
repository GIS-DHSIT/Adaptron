"""Tests for the MSSQL connector."""

from __future__ import annotations

from adaptron.connectors.models import ConnectorConfig, CredentialConfig
from adaptron.connectors.mssql import MSSQLConnector
from adaptron.core.registry import global_registry


def test_registered_as_connector_mssql():
    """Verify that global_registry returns MSSQLConnector for connector/mssql."""
    cls = global_registry.get("connector", "mssql")
    assert cls is MSSQLConnector


def test_mssql_connector_builds_conn_str():
    """Verify _build_conn_str generates correct mssql+pyodbc:// prefix."""
    config = ConnectorConfig(
        connector_type="mssql",
        host="sql.example.com",
        port=1434,
        database="mydb",
        credentials=CredentialConfig(username="sa", password="P@ssw0rd"),
    )
    conn_str = MSSQLConnector._build_conn_str(config)
    assert conn_str == "mssql+pyodbc://sa:P@ssw0rd@sql.example.com:1434/mydb"

    # Test default port
    config_default = ConnectorConfig(
        connector_type="mssql",
        database="testdb",
    )
    conn_str_default = MSSQLConnector._build_conn_str(config_default)
    assert conn_str_default == "mssql+pyodbc://localhost:1433/testdb"
