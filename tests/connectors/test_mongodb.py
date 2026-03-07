"""Tests for the MongoDB connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.mongodb import MongoDBConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_mongodb():
    """Verify that global_registry returns MongoDBConnector for connector/mongodb."""
    cls = global_registry.get("connector", "mongodb")
    assert cls is MongoDBConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock MongoClient and verify DataSchema with correct collections."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.__getitem__ = MagicMock(return_value=mock_db)

    mock_db.list_collection_names.return_value = ["users", "orders"]

    mock_users_coll = MagicMock()
    mock_users_coll.find_one.return_value = {
        "_id": "abc123",
        "name": "Alice",
        "age": 30,
    }
    mock_users_coll.estimated_document_count.return_value = 100

    mock_orders_coll = MagicMock()
    mock_orders_coll.find_one.return_value = {
        "_id": "ord1",
        "total": 49.99,
        "items": [{"sku": "A"}],
    }
    mock_orders_coll.estimated_document_count.return_value = 50

    def db_getitem(name):
        if name == "users":
            return mock_users_coll
        return mock_orders_coll

    mock_db.__getitem__ = MagicMock(side_effect=db_getitem)

    mock_mongo_client_cls = MagicMock(return_value=mock_client)

    config = ConnectorConfig(
        connector_type="mongodb",
        connection_string="mongodb://localhost:27017",
        database="testdb",
    )

    with patch("adaptron.connectors.mongodb.MongoDBConnector.connect") as mock_connect:
        connector = MongoDBConnector()
        connector._client = mock_client
        connector._db = mock_db
        connector._config = config

        schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "mongodb"
    assert schema.database == "testdb"
    assert len(schema.collections) == 2

    users_coll = schema.collections[0]
    assert users_coll.name == "users"
    assert users_coll.source_type == "collection"
    assert users_coll.row_count == 100
    assert any(f.name == "_id" and f.is_primary_key for f in users_coll.fields)
    assert any(f.name == "name" and f.data_type == "string" for f in users_coll.fields)
    assert any(f.name == "age" and f.data_type == "integer" for f in users_coll.fields)

    orders_coll = schema.collections[1]
    assert orders_coll.name == "orders"
    assert orders_coll.row_count == 50
    assert any(f.name == "total" and f.data_type == "float" for f in orders_coll.fields)


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock MongoClient and verify fetch returns correct RawDocuments."""
    mock_db = MagicMock()
    mock_collection = MagicMock()

    docs = [
        {"_id": "1", "name": "Alice", "email": "alice@example.com"},
        {"_id": "2", "name": "Bob", "email": "bob@example.com"},
    ]

    mock_cursor = MagicMock()
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.__iter__ = lambda self: iter(docs)

    mock_collection.find.return_value = mock_cursor
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    config = ConnectorConfig(
        connector_type="mongodb",
        connection_string="mongodb://localhost:27017",
        database="testdb",
    )

    connector = MongoDBConnector()
    connector._client = MagicMock()
    connector._db = mock_db
    connector._config = config

    query = FetchQuery(collection="users", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["name"] == "Alice"
    assert result[0].source_ref == "mongodb://users"
    assert result[0].metadata["collection"] == "users"

    parsed2 = json.loads(result[1].content)
    assert parsed2["name"] == "Bob"
