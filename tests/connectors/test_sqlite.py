"""Tests for the SQLite connector."""

from __future__ import annotations

import sqlite3

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.sqlite import SQLiteConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_sqlite():
    """Verify that global_registry returns SQLiteConnector for connector/sqlite."""
    cls = global_registry.get("connector", "sqlite")
    assert cls is SQLiteConnector


@pytest.mark.asyncio
async def test_sqlite_real_integration(tmp_path):
    """Use a REAL SQLite database: create table, insert data, discover_schema, fetch."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com')")
    conn.execute("INSERT INTO users VALUES (2, 'Bob', 'bob@example.com')")
    conn.commit()
    conn.close()

    config = ConnectorConfig(
        connector_type="sqlite",
        connection_string=f"sqlite:///{db_path}",
    )

    connector = SQLiteConnector()
    await connector.connect(config)

    # Test discover_schema
    schema = await connector.discover_schema()
    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "sqlite"
    assert len(schema.collections) == 1
    assert schema.collections[0].name == "users"
    assert len(schema.collections[0].fields) == 3

    field_names = [f.name for f in schema.collections[0].fields]
    assert "id" in field_names
    assert "name" in field_names
    assert "email" in field_names

    # Test fetch
    query = FetchQuery(collection="users")
    docs = await connector.fetch(query)
    assert len(docs) == 2
    assert isinstance(docs[0], RawDocument)
    assert "Alice" in docs[0].content
    assert docs[0].source_ref == "sqlite://users"
    assert docs[0].metadata["table"] == "users"
    assert docs[0].metadata["row"]["name"] == "Alice"

    assert "Bob" in docs[1].content
    assert docs[1].metadata["row"]["name"] == "Bob"

    await connector.disconnect()


@pytest.mark.asyncio
async def test_sqlite_fetch_with_query(tmp_path):
    """Real SQLite: verify fetch with FetchQuery filters, columns, and limit."""
    db_path = tmp_path / "test2.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    conn.execute("INSERT INTO products VALUES (1, 'Widget', 9.99)")
    conn.execute("INSERT INTO products VALUES (2, 'Gadget', 19.99)")
    conn.execute("INSERT INTO products VALUES (3, 'Gizmo', 29.99)")
    conn.commit()
    conn.close()

    config = ConnectorConfig(
        connector_type="sqlite",
        connection_string=f"sqlite:///{db_path}",
    )

    connector = SQLiteConnector()
    await connector.connect(config)

    # Test with specific columns and limit
    query = FetchQuery(
        collection="products",
        columns=["name", "price"],
        limit=2,
    )
    docs = await connector.fetch(query)
    assert len(docs) == 2
    assert "Widget" in docs[0].content
    assert "Gadget" in docs[1].content

    # Test with filter
    query_filtered = FetchQuery(
        collection="products",
        filters={"name": "Gizmo"},
    )
    docs_filtered = await connector.fetch(query_filtered)
    assert len(docs_filtered) == 1
    assert "Gizmo" in docs_filtered[0].content
    assert docs_filtered[0].metadata["row"]["price"] == 29.99

    await connector.disconnect()
