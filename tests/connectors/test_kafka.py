"""Tests for the Kafka connector."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.models import ConnectorConfig, FetchQuery
from adaptron.connectors.kafka import KafkaConnector
from adaptron.core.registry import global_registry
from adaptron.ingest.models import RawDocument


def test_registered_as_connector_kafka():
    """Verify that global_registry returns KafkaConnector for connector/kafka."""
    cls = global_registry.get("connector", "kafka")
    assert cls is KafkaConnector


def test_supports_streaming():
    """Verify that KafkaConnector.supports_streaming() returns True."""
    connector = KafkaConnector()
    assert connector.supports_streaming() is True


@pytest.mark.asyncio
async def test_fetch_mocked():
    """Mock confluent_kafka Consumer and verify fetch returns correct RawDocuments."""
    mock_consumer = MagicMock()

    # Create mock messages
    msg1 = MagicMock()
    msg1.error.return_value = None
    msg1.value.return_value = b'{"event": "click", "user": "alice"}'
    msg1.partition.return_value = 0
    msg1.offset.return_value = 0

    msg2 = MagicMock()
    msg2.error.return_value = None
    msg2.value.return_value = b'{"event": "view", "user": "bob"}'
    msg2.partition.return_value = 0
    msg2.offset.return_value = 1

    # poll returns messages then None to stop
    mock_consumer.poll.side_effect = [msg1, msg2, None]

    config = ConnectorConfig(
        connector_type="kafka",
        connection_string="localhost:9092",
        options={"group.id": "test-group"},
    )

    connector = KafkaConnector()
    connector._consumer = mock_consumer
    connector._config = config

    query = FetchQuery(collection="events", limit=10)
    result = await connector.fetch(query)

    assert len(result) == 2
    assert isinstance(result[0], RawDocument)
    assert result[0].content == '{"event": "click", "user": "alice"}'
    assert result[0].source_ref == "kafka://events"
    assert result[0].metadata["topic"] == "events"
    assert result[0].metadata["partition"] == 0

    assert result[1].content == '{"event": "view", "user": "bob"}'
