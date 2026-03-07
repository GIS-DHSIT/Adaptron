"""Cassandra connector for schema discovery and data fetching."""

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

_CQL_TYPE_MAP: dict[str, str] = {
    "text": "string",
    "varchar": "string",
    "ascii": "string",
    "int": "integer",
    "bigint": "integer",
    "smallint": "integer",
    "tinyint": "integer",
    "varint": "integer",
    "counter": "integer",
    "float": "float",
    "double": "float",
    "decimal": "float",
    "boolean": "boolean",
    "timestamp": "datetime",
    "date": "datetime",
    "time": "datetime",
    "blob": "binary",
    "list": "json",
    "set": "json",
    "map": "json",
    "uuid": "string",
    "timeuuid": "string",
    "inet": "string",
}


def _cql_type_to_normalized(cql_type: str) -> str:
    """Map a Cassandra CQL type to a normalized type string."""
    # Handle parameterized types like 'list<text>'
    base_type = cql_type.split("<")[0].strip().lower()
    return _CQL_TYPE_MAP.get(base_type, "string")


@register_plugin("connector", "cassandra")
class CassandraConnector(BaseConnector):
    """Connector for Apache Cassandra via the cassandra-driver."""

    def __init__(self) -> None:
        self._cluster: Any = None
        self._session: Any = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            from cassandra.cluster import Cluster
        except ImportError:
            raise RuntimeError(
                "cassandra-driver is required for Cassandra connector. "
                "Install it with: pip install cassandra-driver"
            )
        self._config = config
        host = config.host or "localhost"
        port = config.port or 9042
        self._cluster = Cluster([host], port=port)
        self._session = self._cluster.connect()
        if config.database:
            self._session.set_keyspace(config.database)

    async def disconnect(self) -> None:
        if self._cluster is not None:
            self._cluster.shutdown()
            self._cluster = None
            self._session = None

    async def discover_schema(self) -> DataSchema:
        if self._cluster is None or self._session is None:
            raise RuntimeError("Not connected. Call connect() first.")

        keyspace_name = self._config.database or ""
        if not keyspace_name:
            raise RuntimeError("No keyspace specified in config.database.")

        keyspace_meta = self._cluster.metadata.keyspaces.get(keyspace_name)
        if keyspace_meta is None:
            raise RuntimeError(f"Keyspace '{keyspace_name}' not found.")

        collections: list[CollectionSchema] = []
        for table_name, table_meta in keyspace_meta.tables.items():
            pk_names = {col.name for col in table_meta.primary_key}
            fields: list[FieldInfo] = []
            for col_name, col_meta in table_meta.columns.items():
                cql_type_str = str(col_meta.cql_type)
                fields.append(
                    FieldInfo(
                        name=col_name,
                        data_type=_cql_type_to_normalized(cql_type_str),
                        nullable=col_name not in pk_names,
                        is_primary_key=col_name in pk_names,
                    )
                )
            collections.append(
                CollectionSchema(
                    name=table_name,
                    fields=fields,
                    source_type="table",
                )
            )

        return DataSchema(
            connector_type="cassandra",
            database=keyspace_name,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._session is None:
            raise RuntimeError("Not connected. Call connect() first.")

        if query.raw_query:
            cql = query.raw_query
        else:
            cols = ", ".join(query.columns) if query.columns else "*"
            cql = f"SELECT {cols} FROM {query.collection}"
            if query.filters:
                clauses = [f"{k} = '{v}'" for k, v in query.filters.items()]
                cql += " WHERE " + " AND ".join(clauses)
            if query.limit is not None:
                cql += f" LIMIT {query.limit}"

        rows = self._session.execute(cql)
        documents: list[RawDocument] = []
        for row in rows:
            row_dict = dict(row._asdict()) if hasattr(row, "_asdict") else dict(row)
            content = json.dumps(row_dict, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={"table": query.collection},
                    source_ref=f"cassandra://{query.collection}",
                )
            )

        return documents
