"""Tests for the BigQuery connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.bigquery import BigQueryConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_bigquery():
    """Verify that global_registry returns BigQueryConnector for connector/bigquery."""
    cls = global_registry.get("connector", "bigquery")
    assert cls is BigQueryConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock BigQuery client and verify schema discovery."""
    mock_client = MagicMock()

    # Mock dataset ref
    mock_dataset_ref = MagicMock()
    mock_client.dataset.return_value = mock_dataset_ref

    # Mock table list
    mock_table_item = MagicMock()
    mock_table_item.table_id = "users"
    mock_table_item.reference = "project.dataset.users"
    mock_client.list_tables.return_value = [mock_table_item]

    # Mock table details
    mock_field1 = MagicMock()
    mock_field1.name = "id"
    mock_field1.field_type = "INTEGER"
    mock_field1.mode = "REQUIRED"

    mock_field2 = MagicMock()
    mock_field2.name = "name"
    mock_field2.field_type = "STRING"
    mock_field2.mode = "NULLABLE"

    mock_table = MagicMock()
    mock_table.schema = [mock_field1, mock_field2]
    mock_table.num_rows = 1000
    mock_client.get_table.return_value = mock_table

    config = ConnectorConfig(
        connector_type="bigquery",
        options={"project": "my-project", "dataset": "my_dataset"},
    )

    connector = BigQueryConnector()
    connector._client = mock_client
    connector._config = config
    connector._project = "my-project"
    connector._dataset = "my_dataset"

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "bigquery"
    assert schema.database == "my_dataset"
    assert len(schema.collections) == 1

    users = schema.collections[0]
    assert users.name == "users"
    assert users.source_type == "table"
    assert users.row_count == 1000
    assert any(f.name == "id" and f.data_type == "integer" and not f.nullable for f in users.fields)
    assert any(f.name == "name" and f.data_type == "string" for f in users.fields)


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock BigQuery client and verify fetch returns correct RawDocuments."""
    mock_client = MagicMock()

    mock_row1 = MagicMock()
    mock_row1.__iter__ = lambda self: iter([("id", 1), ("name", "Alice")])
    mock_row1.items = lambda: [("id", 1), ("name", "Alice")]

    mock_row2 = MagicMock()
    mock_row2.__iter__ = lambda self: iter([("id", 2), ("name", "Bob")])
    mock_row2.items = lambda: [("id", 2), ("name", "Bob")]

    # Make rows act as dicts
    def make_row_dict(pairs):
        d = dict(pairs)
        row = MagicMock()
        row.__iter__ = lambda self: iter(d)
        row.__getitem__ = lambda self, k: d[k]
        row.keys = lambda: d.keys()
        row.values = lambda: d.values()
        row.items = lambda: d.items()
        return row

    row1 = make_row_dict([("id", 1), ("name", "Alice")])
    row2 = make_row_dict([("id", 2), ("name", "Bob")])

    mock_result = MagicMock()
    mock_result.__iter__ = lambda self: iter([row1, row2])
    mock_client.query.return_value = mock_result

    config = ConnectorConfig(
        connector_type="bigquery",
        options={"project": "my-project", "dataset": "my_dataset"},
    )

    connector = BigQueryConnector()
    connector._client = mock_client
    connector._config = config
    connector._project = "my-project"
    connector._dataset = "my_dataset"

    query = FetchQuery(collection="users", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["id"] == 1
    assert parsed["name"] == "Alice"
    assert result[0].source_ref == "bigquery://my_dataset/users"
