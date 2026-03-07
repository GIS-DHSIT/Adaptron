"""Stream processor for consuming data from streaming connectors."""
from __future__ import annotations

from adaptron.connectors.base import BaseConnector
from adaptron.connectors.models import FetchQuery
from adaptron.ingest.models import RawDocument


class StreamProcessor:
    """Buffers and batch-processes documents from a streaming connector."""

    def __init__(self, connector: BaseConnector, batch_size: int = 100) -> None:
        self._connector = connector
        self._batch_size = batch_size
        self._running = False
        self._buffer: list[RawDocument] = []

    async def start(self, query: FetchQuery) -> None:
        """Start consuming from streaming connector."""
        self._running = True
        async for doc in self._connector.stream(query):
            if not self._running:
                break
            self._buffer.append(doc)
            if len(self._buffer) >= self._batch_size:
                batch = self._buffer[: self._batch_size]
                self._buffer = self._buffer[self._batch_size :]
                await self.process_batch(batch)

    async def stop(self) -> None:
        """Stop the stream processor."""
        self._running = False

    async def process_batch(self, batch: list[RawDocument]) -> list[RawDocument]:
        """Hook for subclasses to process batches."""
        return batch
