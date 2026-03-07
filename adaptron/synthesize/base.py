from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from adaptron.understand.models import Chunk


class BaseSynthesizer(ABC):
    @abstractmethod
    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]: ...
