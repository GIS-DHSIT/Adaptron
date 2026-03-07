"""S3 connector for schema discovery and data fetching."""

from __future__ import annotations

import csv
import io
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


def _extension(key: str) -> str:
    """Extract file extension from an S3 key."""
    if "." in key:
        return key.rsplit(".", 1)[1].lower()
    return ""


@register_plugin("connector", "s3")
class S3Connector(BaseConnector):
    """Connector for AWS S3 buckets via boto3."""

    def __init__(self) -> None:
        self._client: Any = None
        self._config: ConnectorConfig | None = None
        self._bucket: str = ""
        self._prefix: str = ""

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            import boto3  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "boto3 is required for S3 connector. "
                "Install it with: pip install boto3"
            )
        self._config = config
        self._bucket = config.options.get("bucket", "")
        self._prefix = config.options.get("prefix", "")
        kwargs: dict[str, Any] = {}
        region = config.options.get("region")
        if region:
            kwargs["region_name"] = region
        if config.connection_string:
            kwargs["endpoint_url"] = config.connection_string
        self._client = boto3.client("s3", **kwargs)

    async def disconnect(self) -> None:
        self._client = None

    async def discover_schema(self) -> DataSchema:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        kwargs: dict[str, Any] = {"Bucket": self._bucket}
        if self._prefix:
            kwargs["Prefix"] = self._prefix

        response = self._client.list_objects_v2(**kwargs)
        contents = response.get("Contents", [])

        # Group by file extension
        ext_groups: dict[str, list[str]] = {}
        for obj in contents:
            key = obj["Key"]
            ext = _extension(key)
            if ext:
                ext_groups.setdefault(ext, []).append(key)

        collections: list[CollectionSchema] = []
        for ext, keys in ext_groups.items():
            fields: list[FieldInfo] = []
            if ext == "csv":
                # Try to infer fields from first CSV file
                try:
                    resp = self._client.get_object(Bucket=self._bucket, Key=keys[0])
                    body = resp["Body"].read().decode("utf-8")
                    reader = csv.DictReader(io.StringIO(body))
                    if reader.fieldnames:
                        for col_name in reader.fieldnames:
                            fields.append(
                                FieldInfo(name=col_name, data_type="string", nullable=True)
                            )
                except Exception:
                    pass
            elif ext == "json":
                try:
                    resp = self._client.get_object(Bucket=self._bucket, Key=keys[0])
                    body = resp["Body"].read().decode("utf-8")
                    data = json.loads(body)
                    sample = data[0] if isinstance(data, list) and data else data
                    if isinstance(sample, dict):
                        for k, v in sample.items():
                            dt = "string"
                            if isinstance(v, int):
                                dt = "integer"
                            elif isinstance(v, float):
                                dt = "float"
                            elif isinstance(v, bool):
                                dt = "boolean"
                            fields.append(
                                FieldInfo(name=k, data_type=dt, nullable=True)
                            )
                except Exception:
                    pass

            collections.append(
                CollectionSchema(
                    name=ext,
                    fields=fields,
                    row_count=len(keys),
                    source_type="bucket",
                )
            )

        return DataSchema(
            connector_type="s3",
            database=self._bucket,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        # query.collection is used as a prefix/pattern to match object keys
        kwargs: dict[str, Any] = {"Bucket": self._bucket}
        prefix = query.collection
        if prefix:
            kwargs["Prefix"] = prefix

        response = self._client.list_objects_v2(**kwargs)
        contents = response.get("Contents", [])

        keys = [obj["Key"] for obj in contents]
        if query.limit is not None:
            keys = keys[: query.limit]

        documents: list[RawDocument] = []
        for key in keys:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            body = resp["Body"].read().decode("utf-8")
            ext = _extension(key)

            if ext == "csv":
                reader = csv.DictReader(io.StringIO(body))
                for row in reader:
                    documents.append(
                        RawDocument(
                            content=json.dumps(dict(row)),
                            metadata={"key": key, "format": "csv"},
                            source_ref=f"s3://{self._bucket}/{key}",
                        )
                    )
            elif ext == "json":
                try:
                    data = json.loads(body)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        documents.append(
                            RawDocument(
                                content=json.dumps(item, default=str),
                                metadata={"key": key, "format": "json"},
                                source_ref=f"s3://{self._bucket}/{key}",
                            )
                        )
                except json.JSONDecodeError:
                    documents.append(
                        RawDocument(
                            content=body,
                            metadata={"key": key, "format": "text"},
                            source_ref=f"s3://{self._bucket}/{key}",
                        )
                    )
            else:
                documents.append(
                    RawDocument(
                        content=body,
                        metadata={"key": key, "format": "text"},
                        source_ref=f"s3://{self._bucket}/{key}",
                    )
                )

        return documents
