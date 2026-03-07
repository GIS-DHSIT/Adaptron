"""BigQuery connector for schema discovery and data fetching."""

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

_BQ_TYPE_MAP: dict[str, str] = {
    "STRING": "string",
    "BYTES": "binary",
    "INTEGER": "integer",
    "INT64": "integer",
    "FLOAT": "float",
    "FLOAT64": "float",
    "NUMERIC": "float",
    "BIGNUMERIC": "float",
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "TIMESTAMP": "datetime",
    "DATE": "datetime",
    "TIME": "datetime",
    "DATETIME": "datetime",
    "RECORD": "json",
    "STRUCT": "json",
    "JSON": "json",
}


def _normalize_bq_type(bq_type: str) -> str:
    """Map a BigQuery field type to a normalized type string."""
    return _BQ_TYPE_MAP.get(bq_type.upper(), "string")


@register_plugin("connector", "bigquery")
class BigQueryConnector(BaseConnector):
    """Connector for Google BigQuery."""

    def __init__(self) -> None:
        self._client: Any = None
        self._config: ConnectorConfig | None = None
        self._project: str = ""
        self._dataset: str = ""

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            from google.cloud import bigquery
        except ImportError:
            raise RuntimeError(
                "google-cloud-bigquery is required for BigQuery connector. "
                "Install it with: pip install google-cloud-bigquery"
            )
        self._config = config
        self._project = config.options.get("project", "")
        self._dataset = config.options.get("dataset", config.database or "")
        kwargs: dict[str, Any] = {}
        if self._project:
            kwargs["project"] = self._project
        self._client = bigquery.Client(**kwargs)

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def discover_schema(self) -> DataSchema:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        dataset_ref = self._client.dataset(self._dataset)
        tables = list(self._client.list_tables(dataset_ref))

        collections: list[CollectionSchema] = []
        for table_item in tables:
            table = self._client.get_table(table_item.reference)
            fields: list[FieldInfo] = []
            for field in table.schema:
                fields.append(
                    FieldInfo(
                        name=field.name,
                        data_type=_normalize_bq_type(field.field_type),
                        nullable=(field.mode != "REQUIRED"),
                    )
                )
            collections.append(
                CollectionSchema(
                    name=table_item.table_id,
                    fields=fields,
                    row_count=table.num_rows,
                    source_type="table",
                )
            )

        return DataSchema(
            connector_type="bigquery",
            database=self._dataset,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        if query.raw_query:
            sql = query.raw_query
        else:
            cols = ", ".join(query.columns) if query.columns else "*"
            table_ref = f"`{self._project}.{self._dataset}.{query.collection}`" if self._project else f"`{self._dataset}.{query.collection}`"
            sql = f"SELECT {cols} FROM {table_ref}"

            if query.filters:
                clauses = [f"{k} = @{k}" for k in query.filters]
                sql += " WHERE " + " AND ".join(clauses)

            if query.limit is not None:
                sql += f" LIMIT {query.limit}"

            if query.offset:
                sql += f" OFFSET {query.offset}"

        result = self._client.query(sql)
        documents: list[RawDocument] = []
        for row in result:
            row_dict = dict(row)
            content = json.dumps(row_dict, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={"table": query.collection},
                    source_ref=f"bigquery://{self._dataset}/{query.collection}",
                )
            )

        return documents
