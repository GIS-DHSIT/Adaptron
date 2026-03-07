"""Tests for the Elasticsearch connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.elasticsearch import ElasticsearchConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_elasticsearch():
    """Verify that global_registry returns ElasticsearchConnector for connector/elasticsearch."""
    cls = global_registry.get("connector", "elasticsearch")
    assert cls is ElasticsearchConnector


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock Elasticsearch client and verify schema discovery."""
    mock_client = MagicMock()

    mock_client.indices.get_mapping.return_value = {
        "products": {
            "mappings": {
                "properties": {
                    "name": {"type": "text"},
                    "price": {"type": "float"},
                    "in_stock": {"type": "boolean"},
                    "created_at": {"type": "date"},
                }
            }
        },
        "logs": {
            "mappings": {
                "properties": {
                    "message": {"type": "text"},
                    "level": {"type": "keyword"},
                }
            }
        },
    }

    config = ConnectorConfig(
        connector_type="elasticsearch",
        connection_string="http://localhost:9200",
        database="",
    )

    connector = ElasticsearchConnector()
    connector._client = mock_client
    connector._config = config

    schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "elasticsearch"
    assert len(schema.collections) == 2

    names = [c.name for c in schema.collections]
    assert "products" in names
    assert "logs" in names

    products = next(c for c in schema.collections if c.name == "products")
    assert products.source_type == "index"
    assert len(products.fields) == 4
    assert any(f.name == "name" and f.data_type == "string" for f in products.fields)
    assert any(f.name == "price" and f.data_type == "float" for f in products.fields)
    assert any(f.name == "in_stock" and f.data_type == "boolean" for f in products.fields)
    assert any(f.name == "created_at" and f.data_type == "datetime" for f in products.fields)


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock Elasticsearch client and verify fetch returns correct RawDocuments."""
    mock_client = MagicMock()

    mock_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "1",
                    "_source": {"name": "Widget", "price": 9.99},
                },
                {
                    "_id": "2",
                    "_source": {"name": "Gadget", "price": 19.99},
                },
            ]
        }
    }

    config = ConnectorConfig(
        connector_type="elasticsearch",
        connection_string="http://localhost:9200",
    )

    connector = ElasticsearchConnector()
    connector._client = mock_client
    connector._config = config

    query = FetchQuery(collection="products", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["name"] == "Widget"
    assert parsed["price"] == 9.99
    assert result[0].source_ref == "elasticsearch://products"
    assert result[0].metadata["index"] == "products"
    assert result[0].metadata["id"] == "1"

    parsed2 = json.loads(result[1].content)
    assert parsed2["name"] == "Gadget"
