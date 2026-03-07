"""Snowflake connector for schema discovery and data fetching."""

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

_SF_TYPE_MAP: dict[str, str] = {
    "VARCHAR": "string",
    "STRING": "string",
    "TEXT": "string",
    "CHAR": "string",
    "NUMBER": "float",
    "INT": "integer",
    "INTEGER": "integer",
    "BIGINT": "integer",
    "SMALLINT": "integer",
    "TINYINT": "integer",
    "FLOAT": "float",
    "DOUBLE": "float",
    "REAL": "float",
    "DECIMAL": "float",
    "NUMERIC": "float",
    "BOOLEAN": "boolean",
    "DATE": "datetime",
    "DATETIME": "datetime",
    "TIMESTAMP": "datetime",
    "TIMESTAMP_NTZ": "datetime",
    "TIMESTAMP_LTZ": "datetime",
    "TIMESTAMP_TZ": "datetime",
    "TIME": "datetime",
    "VARIANT": "json",
    "OBJECT": "json",
    "ARRAY": "json",
    "BINARY": "binary",
    "VARBINARY": "binary",
}


def _normalize_sf_type(sf_type: str) -> str:
    """Map a Snowflake column type to a normalized type string."""
    upper = sf_type.upper()
    for key, value in _SF_TYPE_MAP.items():
        if key in upper:
            return value
    return "string"


@register_plugin("connector", "snowflake")
class SnowflakeConnector(BaseConnector):
    """Connector for Snowflake data warehouse."""

    def __init__(self) -> None:
        self._conn: Any = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            import snowflake.connector  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "snowflake-connector-python is required for Snowflake connector. "
                "Install it with: pip install snowflake-connector-python"
            )
        self._config = config
        creds = config.credentials
        self._conn = snowflake.connector.connect(
            account=config.options.get("account", ""),
            user=creds.username if creds else config.options.get("user", ""),
            password=creds.password if creds else config.options.get("password", ""),
            database=config.database or config.options.get("database", ""),
            schema=config.options.get("schema", "PUBLIC"),
            warehouse=config.options.get("warehouse", ""),
        )

    async def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    async def discover_schema(self) -> DataSchema:
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() first.")

        cursor = self._conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        collections: list[CollectionSchema] = []
        for table_row in tables:
            # SHOW TABLES returns table name in column index 1
            table_name = table_row[1]
            cursor.execute(f"DESCRIBE TABLE {table_name}")
            columns = cursor.fetchall()

            fields: list[FieldInfo] = []
            for col_row in columns:
                # DESCRIBE TABLE columns: name, type, kind, null?, default, primary_key, ...
                col_name = col_row[0]
                col_type = col_row[1]
                nullable = col_row[3] == "Y" if len(col_row) > 3 else True
                is_pk = col_row[5] == "Y" if len(col_row) > 5 else False
                fields.append(
                    FieldInfo(
                        name=col_name,
                        data_type=_normalize_sf_type(col_type),
                        nullable=nullable,
                        is_primary_key=is_pk,
                    )
                )

            collections.append(
                CollectionSchema(
                    name=table_name,
                    fields=fields,
                    source_type="table",
                )
            )

        database = self._config.database or "" if self._config else ""
        return DataSchema(
            connector_type="snowflake",
            database=database,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() first.")

        cursor = self._conn.cursor()

        if query.raw_query:
            sql = query.raw_query
        else:
            cols = ", ".join(query.columns) if query.columns else "*"
            sql = f"SELECT {cols} FROM {query.collection}"

            if query.filters:
                clauses = [f"{k} = %({k})s" for k in query.filters]
                sql += " WHERE " + " AND ".join(clauses)

            if query.limit is not None:
                sql += f" LIMIT {query.limit}"

            if query.offset:
                sql += f" OFFSET {query.offset}"

        cursor.execute(sql)
        col_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        documents: list[RawDocument] = []
        for row in rows:
            row_dict = dict(zip(col_names, row))
            content = json.dumps(row_dict, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={"table": query.collection},
                    source_ref=f"snowflake://{query.collection}",
                )
            )

        return documents
