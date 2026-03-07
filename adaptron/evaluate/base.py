from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, Any]: ...
