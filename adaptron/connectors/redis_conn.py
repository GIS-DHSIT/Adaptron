"""Redis connector for schema discovery and data fetching."""

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


def _redis_type_to_normalized(redis_type: str) -> str:
    """Map a Redis key type to a normalized type string."""
    mapping = {
        "string": "string",
        "hash": "json",
        "list": "json",
        "set": "json",
        "zset": "json",
        "stream": "json",
    }
    return mapping.get(redis_type, "string")


@register_plugin("connector", "redis")
class RedisConnector(BaseConnector):
    """Connector for Redis via the redis-py library."""

    def __init__(self) -> None:
        self._client: Any = None
        self._config: ConnectorConfig | None = None

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            import redis as redis_lib
        except ImportError:
            raise RuntimeError(
                "redis is required for Redis connector. "
                "Install it with: pip install redis"
            )
        self._config = config
        if config.connection_string:
            self._client = redis_lib.Redis.from_url(config.connection_string)
        else:
            self._client = redis_lib.Redis(
                host=config.host or "localhost",
                port=config.port or 6379,
                db=int(config.options.get("db", 0)),
            )

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _get_key_value(self, key: str) -> Any:
        """Retrieve a key's value based on its type."""
        key_type = self._client.type(key)
        if isinstance(key_type, bytes):
            key_type = key_type.decode("utf-8")

        if key_type == "string":
            val = self._client.get(key)
            return val.decode("utf-8") if isinstance(val, bytes) else val
        elif key_type == "hash":
            raw = self._client.hgetall(key)
            return {
                (k.decode("utf-8") if isinstance(k, bytes) else k):
                (v.decode("utf-8") if isinstance(v, bytes) else v)
                for k, v in raw.items()
            }
        elif key_type == "list":
            raw = self._client.lrange(key, 0, -1)
            return [v.decode("utf-8") if isinstance(v, bytes) else v for v in raw]
        elif key_type == "set":
            raw = self._client.smembers(key)
            return [v.decode("utf-8") if isinstance(v, bytes) else v for v in raw]
        elif key_type == "zset":
            raw = self._client.zrange(key, 0, -1, withscores=True)
            return [
                (v.decode("utf-8") if isinstance(v, bytes) else v, s)
                for v, s in raw
            ]
        return None

    async def discover_schema(self) -> DataSchema:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        collections: list[CollectionSchema] = []
        cursor = 0
        seen_patterns: dict[str, str] = {}

        while True:
            cursor, keys = self._client.scan(cursor=cursor, count=100)
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                key_type = self._client.type(key)
                if isinstance(key_type, bytes):
                    key_type = key_type.decode("utf-8")
                # Group by key prefix (before the first ':')
                pattern = key.split(":")[0] if ":" in key else key
                if pattern not in seen_patterns:
                    seen_patterns[pattern] = key_type
            if cursor == 0:
                break

        for pattern, key_type in seen_patterns.items():
            fields = [
                FieldInfo(
                    name="value",
                    data_type=_redis_type_to_normalized(key_type),
                    nullable=True,
                )
            ]
            collections.append(
                CollectionSchema(
                    name=pattern,
                    fields=fields,
                    source_type="collection",
                )
            )

        database = self._config.database or "" if self._config else ""
        return DataSchema(
            connector_type="redis",
            database=database,
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        pattern = query.collection
        documents: list[RawDocument] = []
        cursor = 0
        count = 0

        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
            for key in keys:
                if query.limit is not None and count >= query.limit:
                    break
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                value = self._get_key_value(key)
                content = json.dumps({"key": key, "value": value}, default=str)
                documents.append(
                    RawDocument(
                        content=content,
                        metadata={"key": key, "pattern": pattern},
                        source_ref=f"redis://{pattern}",
                    )
                )
                count += 1
            if cursor == 0 or (query.limit is not None and count >= query.limit):
                break

        return documents
