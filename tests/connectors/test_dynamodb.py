"""Tests for the DynamoDB connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.dynamodb import DynamoDBConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_dynamodb():
    """Verify that global_registry returns DynamoDBConnector for connector/dynamodb."""
    cls = global_registry.get("connector", "dynamodb")
    assert cls is DynamoDBConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock boto3 resource and verify schema discovery."""
    mock_resource = MagicMock()
    mock_table = MagicMock()

    mock_table.key_schema = [
        {"AttributeName": "pk", "KeyType": "HASH"},
        {"AttributeName": "sk", "KeyType": "RANGE"},
    ]
    mock_table.attribute_definitions = [
        {"AttributeName": "pk", "AttributeType": "S"},
        {"AttributeName": "sk", "AttributeType": "S"},
    ]
    mock_table.item_count = 500

    mock_resource.Table.return_value = mock_table

    config = ConnectorConfig(
        connector_type="dynamodb",
        database="my_table",
        options={"region": "us-west-2"},
    )

    connector = DynamoDBConnector()
    connector._resource = mock_resource
    connector._config = config

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "dynamodb"
    assert schema.database == "my_table"
    assert len(schema.collections) == 1

    table_schema = schema.collections[0]
    assert table_schema.name == "my_table"
    assert table_schema.source_type == "table"
    assert table_schema.row_count == 500

    pk_field = next(f for f in table_schema.fields if f.name == "pk")
    assert pk_field.is_primary_key is True
    assert pk_field.data_type == "string"
    assert pk_field.nullable is False

    sk_field = next(f for f in table_schema.fields if f.name == "sk")
    assert sk_field.is_primary_key is True


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock boto3 resource and verify fetch returns correct RawDocuments."""
    mock_resource = MagicMock()
    mock_table = MagicMock()

    mock_table.scan.return_value = {
        "Items": [
            {"pk": "user#1", "sk": "profile", "name": "Alice"},
            {"pk": "user#2", "sk": "profile", "name": "Bob"},
        ]
    }

    mock_resource.Table.return_value = mock_table

    config = ConnectorConfig(
        connector_type="dynamodb",
        database="my_table",
        options={"region": "us-west-2"},
    )

    connector = DynamoDBConnector()
    connector._resource = mock_resource
    connector._config = config

    query = FetchQuery(collection="my_table", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["pk"] == "user#1"
    assert parsed["name"] == "Alice"
    assert result[0].source_ref == "dynamodb://my_table"
    assert result[0].metadata["table"] == "my_table"

    parsed2 = json.loads(result[1].content)
    assert parsed2["name"] == "Bob"
