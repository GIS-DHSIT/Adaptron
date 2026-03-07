"""Tests for the REST API connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.connectors.rest_api import RESTAPIConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_rest_api():
    """Verify that global_registry returns RESTAPIConnector for connector/rest_api."""
    cls = global_registry.get("connector", "rest_api")
    assert cls is RESTAPIConnector


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock httpx.get and verify fetch returns correct RawDocuments."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]
    mock_response.raise_for_status = MagicMock()

    config = ConnectorConfig(
        connector_type="rest_api",
        connection_string="https://api.example.com",
        options={"headers": {"Authorization": "Bearer token123"}},
    )

    connector = RESTAPIConnector()
    connector._base_url = "https://api.example.com"
    connector._headers = {"Authorization": "Bearer token123"}
    connector._config = config

    query = FetchQuery(collection="users", limit=10)

    with patch("httpx.get", return_value=mock_response):
        result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)

    parsed = json.loads(result[0].content)
    assert parsed["id"] == 1
    assert parsed["name"] == "Alice"
    assert result[0].source_ref == "rest_api://users"
    assert result[0].metadata["endpoint"] == "users"


@pytest.mark.asyncio
async def test_discover_schema_mocked():
    """Mock httpx.get and verify schema discovery from endpoints."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": 1, "name": "Alice", "active": True},
    ]
    mock_response.raise_for_status = MagicMock()

    config = ConnectorConfig(
        connector_type="rest_api",
        connection_string="https://api.example.com",
        options={
            "endpoints": ["users"],
            "headers": {},
        },
    )

    connector = RESTAPIConnector()
    connector._base_url = "https://api.example.com"
    connector._headers = {}
    connector._config = config

    with patch("httpx.get", return_value=mock_response):
        schema = await connector.discover_schema()

    assert isinstance(schema, DataSchema)
    assert schema.connector_type == "rest_api"
    assert len(schema.collections) == 1

    coll = schema.collections[0]
    assert coll.name == "users"
    assert coll.source_type == "endpoint"
    assert any(f.name == "id" and f.data_type == "integer" for f in coll.fields)
    assert any(f.name == "name" and f.data_type == "string" for f in coll.fields)
    assert any(f.name == "active" and f.data_type == "boolean" for f in coll.fields)
