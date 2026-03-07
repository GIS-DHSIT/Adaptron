"""Tests for the Redshift connector."""

from __future__ import annotations

from adaptron.connectors.models import ConnectorConfig, CredentialConfig
from adaptron.connectors.redshift import RedshiftConnector
from adaptron.core.registry import global_registry


def test_registered_as_connector_redshift():
    """Verify that global_registry returns RedshiftConnector for connector/redshift."""
    cls = global_registry.get("connector", "redshift")
    assert cls is RedshiftConnector


def test_redshift_connector_builds_conn_str():
    """Verify _build_conn_str generates correct redshift+redshift_connector:// prefix."""
    config = ConnectorConfig(
        connector_type="redshift",
        host="redshift-cluster.abc123.us-east-1.redshift.amazonaws.com",
        port=5439,
        database="mydb",
        credentials=CredentialConfig(username="admin", password="S3cret!"),
    )
    conn_str = RedshiftConnector._build_conn_str(config)
    assert conn_str == (
        "redshift+redshift_connector://admin:S3cret!@"
        "redshift-cluster.abc123.us-east-1.redshift.amazonaws.com:5439/mydb"
    )

    # Test default port
    config_default = ConnectorConfig(
        connector_type="redshift",
        database="testdb",
    )
    conn_str_default = RedshiftConnector._build_conn_str(config_default)
    assert conn_str_default == "redshift+redshift_connector://localhost:5439/testdb"
