"""DynamoDB connector for schema discovery and data fetching."""

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

_DYNAMO_TYPE_MAP: dict[str, str] = {
    "S": "string",
    "N": "float",
    "B": "binary",
    "BOOL": "boolean",
    "L": "json",
    "M": "json",
    "SS": "json",
    "NS": "json",
    "BS": "json",
}


def _dynamo_type_to_normalized(attr_type: str) -> str:
    """Map a DynamoDB attribute type to a normalized type string."""
    return _DYNAMO_TYPE_MAP.get(attr_type, "string")


@register_plugin("connector", "dynamodb")
class DynamoDBConnector(BaseConnector):
    """Connector for AWS DynamoDB via boto3."""

    def __init__(self) -> None:
        self._resource: Any = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            import boto3
        except ImportError:
            raise RuntimeError(
                "boto3 is required for DynamoDB connector. "
                "Install it with: pip install boto3"
            )
        self._config = config
        region = config.options.get("region", "us-east-1")
        kwargs: dict[str, Any] = {"region_name": region}
        if config.connection_string:
            kwargs["endpoint_url"] = config.connection_string
        self._resource = boto3.resource("dynamodb", **kwargs)

    async def disconnect(self) -> None:
        # boto3 manages connections internally; no explicit close needed.
        self._resource = None

    async def discover_schema(self) -> DataSchema:
        if self._resource is None:
            raise RuntimeError("Not connected. Call connect() first.")

        table_name = self._config.database or self._config.options.get("table", "")
        if not table_name:
            raise RuntimeError("No table specified in config.database or config.options['table'].")

        table = self._resource.Table(table_name)
        table.load()

        key_schema = table.key_schema or []
        attr_defs = table.attribute_definitions or []

        key_names = {ks["AttributeName"] for ks in key_schema}
        attr_type_map = {ad["AttributeName"]: ad["AttributeType"] for ad in attr_defs}

        fields: list[FieldInfo] = []
        for attr_name, attr_type in attr_type_map.items():
            fields.append(
                FieldInfo(
                    name=attr_name,
                    data_type=_dynamo_type_to_normalized(attr_type),
                    nullable=attr_name not in key_names,
                    is_primary_key=attr_name in key_names,
                )
            )

        row_count = table.item_count if hasattr(table, "item_count") else None

        collections = [
            CollectionSchema(
                name=table_name,
                fields=fields,
                row_count=row_count,
                source_type="table",
            )
        ]

        return DataSchema(
            connector_type="dynamodb",
            database=table_name,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._resource is None:
            raise RuntimeError("Not connected. Call connect() first.")

        table = self._resource.Table(query.collection)
        scan_kwargs: dict[str, Any] = {}

        if query.filters:
            from boto3.dynamodb.conditions import Attr
            filter_expr = None
            for k, v in query.filters.items():
                condition = Attr(k).eq(v)
                filter_expr = condition if filter_expr is None else filter_expr & condition
            scan_kwargs["FilterExpression"] = filter_expr

        if query.limit is not None:
            scan_kwargs["Limit"] = query.limit

        if query.columns:
            scan_kwargs["ProjectionExpression"] = ", ".join(query.columns)

        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        documents: list[RawDocument] = []
        for item in items:
            content = json.dumps(item, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={"table": query.collection},
                    source_ref=f"dynamodb://{query.collection}",
                )
            )

        return documents
