"""Tests for the MySQL connector."""

from __future__ import annotations

from adaptron.connectors.models import ConnectorConfig, CredentialConfig
from adaptron.connectors.mysql import MySQLConnector
from adaptron.core.registry import global_registry


def test_registered_as_connector_mysql():
    """Verify that global_registry returns MySQLConnector for connector/mysql."""
    cls = global_registry.get("connector", "mysql")
    assert cls is MySQLConnector


def test_mysql_connector_builds_conn_str():
    """Verify _build_conn_str generates correct mysql+pymysql:// prefix."""
    config = ConnectorConfig(
        connector_type="mysql",
        host="db.example.com",
        port=3307,
        database="mydb",
        credentials=CredentialConfig(username="admin", password="secret"),
    )
    conn_str = MySQLConnector._build_conn_str(config)
    assert conn_str == "mysql+pymysql://admin:secret@db.example.com:3307/mydb"

    # Test default port
    config_default = ConnectorConfig(
        connector_type="mysql",
        database="testdb",
    )
    conn_str_default = MySQLConnector._build_conn_str(config_default)
    assert conn_str_default == "mysql+pymysql://localhost:3306/testdb"
