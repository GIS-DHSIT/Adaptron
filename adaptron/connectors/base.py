from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from adaptron.connectors.models import ConnectorConfig, DataSchema, FetchQuery
from adaptron.ingest.models import RawDocument


class BaseConnector(ABC):
    @abstractmethod
    async def connect(self, config: ConnectorConfig) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def fetch(self, query: FetchQuery) -> list[RawDocument]: ...

    async def stream(self, query: FetchQuery) -> AsyncIterator[RawDocument]:
        raise NotImplementedError("This connector does not support streaming")
        yield  # makes it an async generator

    @abstractmethod
    async def discover_schema(self) -> DataSchema: ...

    def supports_streaming(self) -> bool:
        return False
