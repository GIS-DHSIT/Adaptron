"""REST API connector for schema discovery and data fetching."""

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

_PYTHON_TYPE_MAP: dict[type, str] = {
    bool: "boolean",  # must come before int since bool is subclass of int
    int: "integer",
    float: "float",
    str: "string",
    list: "json",
    dict: "json",
}


def _infer_field_type(value: Any) -> str:
    """Infer normalized type from a Python value."""
    for py_type, norm in _PYTHON_TYPE_MAP.items():
        if isinstance(value, py_type):
            return norm
    return "string"


@register_plugin("connector", "rest_api")
class RESTAPIConnector(BaseConnector):
    """Connector for REST APIs via httpx."""

    def __init__(self) -> None:
        self._base_url: str = ""
        self._headers: dict[str, str] = {}
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            import httpx  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "httpx is required for REST API connector. "
                "Install it with: pip install httpx"
            )
        self._config = config
        self._base_url = config.connection_string or config.options.get("base_url", "")
        self._headers = config.options.get("headers", {})

    async def disconnect(self) -> None:
        # No persistent connection to close
        pass

    async def discover_schema(self) -> DataSchema:
        if not self._base_url:
            raise RuntimeError("Not connected. Call connect() first.")

        import httpx

        endpoints: list[str] = (self._config.options.get("endpoints", [])
                                if self._config else [])
        collections: list[CollectionSchema] = []

        for endpoint in endpoints:
            url = self._base_url.rstrip("/") + "/" + endpoint.lstrip("/")
            response = httpx.get(url, headers=self._headers)
            response.raise_for_status()
            data = response.json()

            fields: list[FieldInfo] = []
            items = data if isinstance(data, list) else [data]
            if items:
                sample = items[0]
                if isinstance(sample, dict):
                    for key, value in sample.items():
                        fields.append(
                            FieldInfo(
                                name=key,
                                data_type=_infer_field_type(value),
                                nullable=True,
                            )
                        )

            collections.append(
                CollectionSchema(
                    name=endpoint,
                    fields=fields,
                    row_count=len(items) if isinstance(data, list) else 1,
                    source_type="endpoint",
                )
            )

        return DataSchema(
            connector_type="rest_api",
            database=self._base_url,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if not self._base_url:
            raise RuntimeError("Not connected. Call connect() first.")

        import httpx

        url = self._base_url.rstrip("/") + "/" + query.collection.lstrip("/")
        params: dict[str, Any] = {}
        if query.filters:
            params.update(query.filters)

        response = httpx.get(url, headers=self._headers, params=params)
        response.raise_for_status()
        data = response.json()

        items = data if isinstance(data, list) else [data]
        if query.limit is not None:
            items = items[: query.limit]

        documents: list[RawDocument] = []
        for item in items:
            content = json.dumps(item, default=str)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={"endpoint": query.collection},
                    source_ref=f"rest_api://{query.collection}",
                )
            )

        return documents
