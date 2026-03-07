import pytest
from unittest.mock import MagicMock
from adaptron.connectors.stream import StreamProcessor
from adaptron.ingest.models import RawDocument


@pytest.mark.asyncio
async def test_batch_buffering():
    mock_connector = MagicMock()
    processor = StreamProcessor(connector=mock_connector, batch_size=2)

    # Manually add docs to buffer and check batching
    doc1 = RawDocument(content="doc1", source_ref="s1")
    doc2 = RawDocument(content="doc2", source_ref="s2")

    processor._buffer.append(doc1)
    assert len(processor._buffer) == 1
    processor._buffer.append(doc2)
    assert len(processor._buffer) == 2

    # Process the batch
    batch = await processor.process_batch(processor._buffer[:])
    assert len(batch) == 2


@pytest.mark.asyncio
async def test_stop_lifecycle():
    mock_connector = MagicMock()
    processor = StreamProcessor(connector=mock_connector, batch_size=100)
    assert processor._running is False
    processor._running = True
    assert processor._running is True
    await processor.stop()
    assert processor._running is False
