"""Tests for the Redis connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.redis_conn import RedisConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_redis():
    """Verify that global_registry returns RedisConnector for connector/redis."""
    cls = global_registry.get("connector", "redis")
    assert cls is RedisConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock Redis client and verify schema discovery."""
    mock_client = MagicMock()

    # Simulate SCAN returning keys
    mock_client.scan.side_effect = [
        (0, [b"user:1", b"user:2", b"session:abc"]),
    ]
    mock_client.type.side_effect = [b"hash", b"hash", b"string"]

    config = ConnectorConfig(
        connector_type="redis",
        connection_string="redis://localhost:6379",
    )

    connector = RedisConnector()
    connector._client = mock_client
    connector._config = config

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "redis"
    assert len(schema.collections) == 2

    names = [c.name for c in schema.collections]
    assert "user" in names
    assert "session" in names

    user_coll = next(c for c in schema.collections if c.name == "user")
    assert user_coll.fields[0].data_type == "json"  # hash -> json

    session_coll = next(c for c in schema.collections if c.name == "session")
    assert session_coll.fields[0].data_type == "string"


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock Redis client and verify fetch returns correct RawDocuments."""
    mock_client = MagicMock()

    # SCAN returns matching keys
    mock_client.scan.side_effect = [
        (0, [b"user:1", b"user:2"]),
    ]
    mock_client.type.side_effect = [b"string", b"string"]
    mock_client.get.side_effect = [b"Alice", b"Bob"]

    config = ConnectorConfig(
        connector_type="redis",
        connection_string="redis://localhost:6379",
    )

    connector = RedisConnector()
    connector._client = mock_client
    connector._config = config

    query = FetchQuery(collection="user:*", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["key"] == "user:1"
    assert parsed["value"] == "Alice"
    assert result[0].source_ref == "redis://user:*"

    parsed2 = json.loads(result[1].content)
    assert parsed2["value"] == "Bob"
