"""Tests for the Cassandra connector."""

from __future__ import annotations

import json
from collections import namedtuple
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.cassandra import CassandraConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_cassandra():
    """Verify that global_registry returns CassandraConnector for connector/cassandra."""
    cls = global_registry.get("connector", "cassandra")
    assert cls is CassandraConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock Cassandra Cluster and verify schema discovery."""
    mock_cluster = MagicMock()
    mock_session = MagicMock()

    # Mock column metadata
    mock_col_id = MagicMock()
    mock_col_id.name = "id"
    mock_col_id.cql_type = "uuid"

    mock_col_name = MagicMock()
    mock_col_name.name = "name"
    mock_col_name.cql_type = "text"

    mock_col_age = MagicMock()
    mock_col_age.name = "age"
    mock_col_age.cql_type = "int"

    # Mock primary key
    mock_pk_col = MagicMock()
    mock_pk_col.name = "id"

    # Mock table metadata
    mock_table = MagicMock()
    mock_table.columns = {"id": mock_col_id, "name": mock_col_name, "age": mock_col_age}
    mock_table.primary_key = [mock_pk_col]

    # Mock keyspace metadata
    mock_keyspace = MagicMock()
    mock_keyspace.tables = {"users": mock_table}

    mock_cluster.metadata.keyspaces = {"test_ks": mock_keyspace}

    config = ConnectorConfig(
        connector_type="cassandra",
        host="localhost",
        port=9042,
        database="test_ks",
    )

    connector = CassandraConnector()
    connector._cluster = mock_cluster
    connector._session = mock_session
    connector._config = config

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "cassandra"
    assert schema.database == "test_ks"
    assert len(schema.collections) == 1

    users_table = schema.collections[0]
    assert users_table.name == "users"
    assert users_table.source_type == "table"

    id_field = next(f for f in users_table.fields if f.name == "id")
    assert id_field.is_primary_key is True
    assert id_field.data_type == "string"  # uuid -> string

    name_field = next(f for f in users_table.fields if f.name == "name")
    assert name_field.data_type == "string"
    assert name_field.is_primary_key is False

    age_field = next(f for f in users_table.fields if f.name == "age")
    assert age_field.data_type == "integer"


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock Cassandra session and verify fetch returns correct RawDocuments."""
    mock_session = MagicMock()
    mock_cluster = MagicMock()

    Row = namedtuple("Row", ["id", "name", "age"])
    rows = [
        Row(id="uuid-1", name="Alice", age=30),
        Row(id="uuid-2", name="Bob", age=25),
    ]

    mock_session.execute.return_value = rows

    config = ConnectorConfig(
        connector_type="cassandra",
        host="localhost",
        port=9042,
        database="test_ks",
    )

    connector = CassandraConnector()
    connector._cluster = mock_cluster
    connector._session = mock_session
    connector._config = config

    query = FetchQuery(collection="users", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["name"] == "Alice"
    assert parsed["id"] == "uuid-1"
    assert result[0].source_ref == "cassandra://users"
    assert result[0].metadata["table"] == "users"

    parsed2 = json.loads(result[1].content)
    assert parsed2["name"] == "Bob"
    assert parsed2["age"] == 25
