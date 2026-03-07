"""Kafka connector for schema discovery, fetching, and streaming."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

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


@register_plugin("connector", "kafka")
class KafkaConnector(BaseConnector):
    """Connector for Apache Kafka via confluent-kafka."""

    def __init__(self) -> None:
        self._consumer: Any = None
        self._config: ConnectorConfig | None = None

    def supports_streaming(self) -> bool:
        return True

    async def connect(self, config: ConnectorConfig) -> None:
        try:
            from confluent_kafka import Consumer  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "confluent-kafka is required for Kafka connector. "
                "Install it with: pip install confluent-kafka"
            )
        self._config = config
        bootstrap_servers = config.connection_string or config.options.get(
            "bootstrap.servers", "localhost:9092"
        )
        group_id = config.options.get("group.id", "adaptron-consumer")
        consumer_config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": config.options.get("auto.offset.reset", "earliest"),
        }
        self._consumer = Consumer(consumer_config)

    async def disconnect(self) -> None:
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

    async def discover_schema(self) -> DataSchema:
        if self._consumer is None:
            raise RuntimeError("Not connected. Call connect() first.")

        cluster_meta = self._consumer.list_topics()
        collections: list[CollectionSchema] = []
        for topic_name in cluster_meta.topics:
            collections.append(
                CollectionSchema(
                    name=topic_name,
                    fields=[],
                    source_type="topic",
                )
            )

        return DataSchema(
            connector_type="kafka",
            database=self._config.connection_string or "" if self._config else "",
            collections=collections,
        )

    async def fetch(self, query: FetchQuery) -> list[RawDocument]:
        if self._consumer is None:
            raise RuntimeError("Not connected. Call connect() first.")

        self._consumer.subscribe([query.collection])
        limit = query.limit or 100
        documents: list[RawDocument] = []

        while len(documents) < limit:
            msg = self._consumer.poll(timeout=1.0)
            if msg is None:
                break
            if msg.error():
                continue
            value = msg.value()
            if value is None:
                continue

            content = value.decode("utf-8") if isinstance(value, bytes) else str(value)
            documents.append(
                RawDocument(
                    content=content,
                    metadata={
                        "topic": query.collection,
                        "partition": msg.partition(),
                        "offset": msg.offset(),
                    },
                    source_ref=f"kafka://{query.collection}",
                )
            )

        return documents

    async def stream(self, query: FetchQuery) -> AsyncIterator[RawDocument]:
        if self._consumer is None:
            raise RuntimeError("Not connected. Call connect() first.")

        self._consumer.subscribe([query.collection])

        while True:
            msg = self._consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                continue
            value = msg.value()
            if value is None:
                continue

            content = value.decode("utf-8") if isinstance(value, bytes) else str(value)
            yield RawDocument(
                content=content,
                metadata={
                    "topic": query.collection,
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                },
                source_ref=f"kafka://{query.collection}",
            )
