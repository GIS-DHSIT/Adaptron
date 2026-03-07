"""Tests for the S3 connector."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.s3 import S3Connector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_s3():
    """Verify that global_registry returns S3Connector for connector/s3."""
    cls = global_registry.get("connector", "s3")
    assert cls is S3Connector


@pytest.mark.asyncio
async def test_list_objects_mocked():
    """Mock boto3 S3 client and verify discover_schema groups by extension."""
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "data/file1.csv"},
            {"Key": "data/file2.csv"},
            {"Key": "data/records.json"},
        ]
    }

    # Mock get_object for CSV schema inference
    csv_body = MagicMock()
    csv_body.read.return_value = b"name,age,email\nAlice,30,alice@test.com\n"
    mock_client.get_object.return_value = {"Body": csv_body}

    config = ConnectorConfig(
        connector_type="s3",
        options={"bucket": "my-bucket", "prefix": "data/"},
    )

    connector = S3Connector()
    connector._client = mock_client
    connector._config = config
    connector._bucket = "my-bucket"
    connector._prefix = "data/"

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "s3"
    assert schema.database == "my-bucket"

    # Should have two collections: csv and json
    assert len(schema.collections) == 2
    ext_names = {c.name for c in schema.collections}
    assert "csv" in ext_names
    assert "json" in ext_names

    csv_coll = next(c for c in schema.collections if c.name == "csv")
    assert csv_coll.row_count == 2
    assert csv_coll.source_type == "bucket"


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock boto3 S3 client and verify fetch downloads and parses files."""
    mock_client = MagicMock()

    # list_objects_v2 for the prefix
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "data/records.json"},
        ]
    }

    # get_object returns JSON content
    json_data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    json_body = MagicMock()
    json_body.read.return_value = json.dumps(json_data).encode("utf-8")
    mock_client.get_object.return_value = {"Body": json_body}

    config = ConnectorConfig(
        connector_type="s3",
        options={"bucket": "my-bucket", "prefix": "data/"},
    )

    connector = S3Connector()
    connector._client = mock_client
    connector._config = config
    connector._bucket = "my-bucket"
    connector._prefix = "data/"

    query = FetchQuery(collection="data/records.json", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["id"] == 1
    assert parsed["name"] == "Alice"
    assert result[0].source_ref == "s3://my-bucket/data/records.json"
    assert result[0].metadata["format"] == "json"
