"""Tests for the Snowflake connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery, CredentialConfig
from adaptron.connectors.snowflake import SnowflakeConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_snowflake():
    """Verify that global_registry returns SnowflakeConnector for connector/snowflake."""
    cls = global_registry.get("connector", "snowflake")
    assert cls is SnowflakeConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock snowflake connection and verify schema discovery."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # SHOW TABLES returns rows with table name at index 1
    show_tables_result = [
        (None, "users", None, None),
        (None, "orders", None, None),
    ]

    describe_users = [
        ("id", "NUMBER(38,0)", "COLUMN", "N", None, "Y"),
        ("name", "VARCHAR(256)", "COLUMN", "Y", None, "N"),
        ("email", "VARCHAR(256)", "COLUMN", "Y", None, "N"),
    ]

    describe_orders = [
        ("order_id", "NUMBER(38,0)", "COLUMN", "N", None, "Y"),
        ("total", "FLOAT", "COLUMN", "Y", None, "N"),
    ]

    def execute_side_effect(sql):
        pass

    def fetchall_side_effect():
        call_count = mock_cursor.execute.call_count
        if call_count == 1:
            return show_tables_result
        elif call_count == 2:
            return describe_users
        elif call_count == 3:
            return describe_orders
        return []

    mock_cursor.execute.side_effect = execute_side_effect
    mock_cursor.fetchall.side_effect = fetchall_side_effect

    config = ConnectorConfig(
        connector_type="snowflake",
        database="my_db",
        options={"account": "abc123", "schema": "PUBLIC", "warehouse": "COMPUTE_WH"},
    )

    connector = SnowflakeConnector()
    connector._conn = mock_conn
    connector._config = config

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "snowflake"
    assert schema.database == "my_db"
    assert len(schema.collections) == 2

    users = schema.collections[0]
    assert users.name == "users"
    assert users.source_type == "table"
    assert any(f.name == "id" and f.data_type == "float" for f in users.fields)  # NUMBER -> float
    assert any(f.name == "name" and f.data_type == "string" for f in users.fields)


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock snowflake connection and verify fetch returns correct RawDocuments."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.description = [("id",), ("name",), ("email",)]
    mock_cursor.fetchall.return_value = [
        (1, "Alice", "alice@example.com"),
        (2, "Bob", "bob@example.com"),
    ]

    config = ConnectorConfig(
        connector_type="snowflake",
        database="my_db",
        options={"account": "abc123"},
    )

    connector = SnowflakeConnector()
    connector._conn = mock_conn
    connector._config = config

    query = FetchQuery(collection="users", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["id"] == 1
    assert parsed["name"] == "Alice"
    assert result[0].source_ref == "snowflake://users"
    assert result[0].metadata["table"] == "users"
