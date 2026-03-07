"""MongoDB connector for schema discovery and data fetching."""

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

_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "float",
    bool: "boolean",
    list: "json",
    dict: "json",
    bytes: "binary",
}


def _python_type_to_normalized(value: Any) -> str:
    """Map a Python value's type to a normalized type string."""
    for py_type, norm in _TYPE_MAP.items():
        if isinstance(value, py_type):
            return norm
    return "string"


@register_plugin("connector", "mongodb")
class MongoDBConnector(BaseConnector):
    """Connector for MongoDB databases via pymongo."""

    def __init__(self) -> None:
        self._client: Any = None
        self._db: Any = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            from pymongo import MongoClient
        except ImportError:
            raise RuntimeError(
                "pymongo is required for MongoDB connector. "
                "Install it with: pip install pymongo"
            )
        self._config = config
        conn_str = config.connection_string or f"mongodb://{config.host or 'localhost'}:{config.port or 27017}"
        self._client = MongoClient(conn_str)
        self._db = self._client[config.database or "test"]

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None

    async def discover_schema(self) -> DataSchema:
        if self._db is None:
            raise RuntimeError("Not connected. Call connect() first.")

        collections: list[CollectionSchema] = []
        for coll_name in self._db.list_collection_names():
            collection = self._db[coll_name]
            fields: list[FieldInfo] = []

            # Sample one document to infer schema
            sample = collection.find_one()
            if sample:
                for key, value in sample.items():
                    fields.append(
                        FieldInfo(
                            name=key,
                            data_type=_python_type_to_normalized(value),
                            nullable=True,
                            is_primary_key=(key == "_id"),
                        )
                    )

            row_count = collection.estimated_document_count()
            collections.append(
                CollectionSchema(
                    name=coll_name,
                    fields=fields,
                    row_count=row_count,
                    source_type="collection",
                )
            )

        database = self._config.database or "" if self._config else ""
        return DataSchema(
            connector_type="mongodb",
            database=database,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._db is None:
            raise RuntimeError("Not connected. Call connect() first.")

        collection = self._db[query.collection]
        filters = query.filters or {}
        projection = {col: 1 for col in query.columns} if query.columns else None

        cursor = collection.find(filters, projection)

        if query.offset:
            cursor = cursor.skip(query.offset)
        if query.limit is not None:
            cursor = cursor.limit(query.limit)

        documents: list[RawDocument] = []
        for doc in cursor:
            content = json.dumps(doc, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={"collection": query.collection},
                    source_ref=f"mongodb://{query.collection}",
                )
            )

        return documents
