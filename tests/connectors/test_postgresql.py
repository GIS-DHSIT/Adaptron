"""Tests for the PostgreSQL connector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import (
    CollectionSchema,
    ConnectorConfig,
    CredentialConfig,
    DataSchema,
    FetchQuery,
    FieldInfo,
)
from adaptron.connectors.postgresql import PostgreSQLConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_postgresql():
    """Verify that global_registry returns PostgreSQLConnector for connector/postgresql."""
    cls = global_registry.get("connector", "postgresql")
    assert cls is PostgreSQLConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock create_engine and inspect, verify DataSchema with correct collections."""
    mock_engine = MagicMock()
    mock_inspector = MagicMock()

    # Setup inspector return values
    mock_inspector.get_table_names.return_value = ["users", "orders"]

    mock_inspector.get_columns.side_effect = [
        # users table
        [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "name", "type": "VARCHAR(100)", "nullable": True},
        ],
        # orders table
        [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "user_id", "type": "INTEGER", "nullable": False},
            {"name": "total", "type": "NUMERIC(10,2)", "nullable": True},
        ],
    ]

    mock_inspector.get_pk_constraint.side_effect = [
        {"constrained_columns": ["id"]},
        {"constrained_columns": ["id"]},
    ]

    mock_inspector.get_foreign_keys.side_effect = [
        [],  # users has no FKs
        [{"referred_table": "users", "constrained_columns": ["user_id"]}],
    ]

    # Mock sample query results
    mock_conn = MagicMock()
    mock_result_users = MagicMock()
    mock_result_users.keys.return_value = ["id", "name"]
    mock_result_users.__iter__ = lambda self: iter([(1, "Alice"), (2, "Bob")])

    mock_result_orders = MagicMock()
    mock_result_orders.keys.return_value = ["id", "user_id", "total"]
    mock_result_orders.__iter__ = lambda self: iter([(1, 1, 99.99)])

    mock_conn.execute.side_effect = [mock_result_users, mock_result_orders]
    mock_engine.connect.return_value.__enter__ = lambda self: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    config = ConnectorConfig(
        connector_type="postgresql",
        connection_string="postgresql://user:pass@localhost:5432/testdb",
        database="testdb",
    )

    with patch("adaptron.connectors.postgresql.create_engine", return_value=mock_engine), \
         patch("adaptron.connectors.postgresql.inspect", return_value=mock_inspector):
        connector = PostgreSQLConnector()
        await connector.connect(config)
        schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "postgresql"
    assert schema.database == "testdb"
    assert len(schema.collections) == 2

    users_coll = schema.collections[0]
    assert users_coll.name == "users"
    assert users_coll.source_type == "table"
    assert len(users_coll.fields) == 2
    assert users_coll.fields[0].name == "id"
    assert users_coll.fields[0].is_primary_key is True
    assert users_coll.fields[0].data_type == "integer"
    assert users_coll.fields[0].sample_values == [1, 2]

    orders_coll = schema.collections[1]
    assert orders_coll.name == "orders"
    assert "users" in orders_coll.relationships
    assert orders_coll.fields[2].name == "total"
    assert orders_coll.fields[2].data_type == "float"


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock engine + connection, verify returns RawDocuments with correct content."""
    mock_engine = MagicMock()
    mock_conn = MagicMock()

    mock_result = MagicMock()
    mock_result.keys.return_value = ["id", "name", "email"]
    mock_result.__iter__ = lambda self: iter([
        (1, "Alice", "alice@example.com"),
        (2, "Bob", "bob@example.com"),
    ])

    mock_conn.execute.return_value = mock_result
    mock_engine.connect.return_value.__enter__ = lambda self: mock_conn
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    config = ConnectorConfig(
        connector_type="postgresql",
        connection_string="postgresql://user:pass@localhost:5432/testdb",
    )

    query = FetchQuery(
        collection="users",
        columns=["id", "name", "email"],
        limit=10,
    )

    with patch("adaptron.connectors.postgresql.create_engine", return_value=mock_engine):
        connector = PostgreSQLConnector()
        await connector.connect(config)
        docs = await connector.fetch(query)

    assert len(docs) == 2

    assert isinstance(docs[0], RawDocument)
    assert "id=1" in docs[0].content
    assert "name=Alice" in docs[0].content
    assert "email=alice@example.com" in docs[0].content
    assert docs[0].metadata["table"] == "users"
    assert docs[0].metadata["columns"] == ["id", "name", "email"]
    assert docs[0].metadata["row"] == {"id": 1, "name": "Alice", "email": "alice@example.com"}
    assert docs[0].source_ref == "postgresql://users"

    assert "id=2" in docs[1].content
    assert "name=Bob" in docs[1].content
