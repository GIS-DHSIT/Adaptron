from __future__ import annotations

from abc import ABC, abstractmethod

from adaptron.ingest.models import DataSource, RawDocument


class BaseIngester(ABC):
    @abstractmethod
    def ingest(self, source: DataSource) -> list[RawDocument]: ...

    @abstractmethod
    def supported_types(self) -> list[str]: ...
