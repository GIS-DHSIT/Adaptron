"""Elasticsearch connector for schema discovery and data fetching."""

from __future__ import annotations

import json
from typing import Any

from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import (
    CollectionSchema,
    ConnectorConfig,
    DataSchema,
    FetchQuery,
    FieldInfo,
)
from adaptron.core.registry import register_plugin
from adaptron.ingest.models import RawDocument

_ES_TYPE_MAP: dict[str, str] = {
    "text": "string",
    "keyword": "string",
    "long": "integer",
    "integer": "integer",
    "short": "integer",
    "byte": "integer",
    "float": "float",
    "double": "float",
    "half_float": "float",
    "scaled_float": "float",
    "boolean": "boolean",
    "date": "datetime",
    "object": "json",
    "nested": "json",
    "binary": "binary",
}


def _es_type_to_normalized(es_type: str) -> str:
    """Map an Elasticsearch field type to a normalized type string."""
    return _ES_TYPE_MAP.get(es_type, "string")


@register_plugin("connector", "elasticsearch")
class ElasticsearchConnector(BaseConnector):
    """Connector for Elasticsearch."""

    def __init__(self) -> None:
        self._client: Any = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            raise RuntimeError(
                "elasticsearch is required for Elasticsearch connector. "
                "Install it with: pip install elasticsearch"
            )
        self._config = config
        if config.connection_string:
            self._client = Elasticsearch(config.connection_string)
        else:
            host = config.host or "localhost"
            port = config.port or 9200
            self._client = Elasticsearch(f"http://{host}:{port}")

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def discover_schema(self) -> DataSchema:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        mappings = self._client.indices.get_mapping(index="*")
        collections: list[CollectionSchema] = []

        for index_name, index_data in mappings.items():
            properties = (
                index_data.get("mappings", {}).get("properties", {})
            )
            fields: list[FieldInfo] = []
            for field_name, field_meta in properties.items():
                es_type = field_meta.get("type", "object")
                fields.append(
                    FieldInfo(
                        name=field_name,
                        data_type=_es_type_to_normalized(es_type),
                        nullable=True,
                    )
                )
            collections.append(
                CollectionSchema(
                    name=index_name,
                    fields=fields,
                    source_type="index",
                )
            )

        database = self._config.database or "" if self._config else ""
        return DataSchema(
            connector_type="elasticsearch",
            database=database,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        if query.raw_query:
            body = json.loads(query.raw_query) if isinstance(query.raw_query, str) else query.raw_query
        else:
            body: dict[str, Any] = {"query": {"match_all": {}}}
            if query.filters:
                must_clauses = [
                    {"match": {k: v}} for k, v in query.filters.items()
                ]
                body = {"query": {"bool": {"must": must_clauses}}}

        kwargs: dict[str, Any] = {"index": query.collection, "body": body}
        if query.limit is not None:
            kwargs["size"] = query.limit
        if query.offset:
            kwargs["from_"] = query.offset

        result = self._client.search(**kwargs)
        hits = result.get("hits", {}).get("hits", [])

        documents: list[RawDocument] = []
        for hit in hits:
            source = hit.get("_source", {})
            content = json.dumps(source, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={
                        "index": query.collection,
                        "id": hit.get("_id"),
                    },
                    source_ref=f"elasticsearch://{query.collection}",
                )
            )

        return documents
