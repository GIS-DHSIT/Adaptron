from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from adaptron.core.events import EventBus
from adaptron.train.models import TrainConfig, TrainResult


class BaseTrainer(ABC):
    @abstractmethod
    async def train(
        self,
        config: TrainConfig,
        dataset: list[dict[str, Any]],
        event_bus: EventBus | None = None,
    ) -> TrainResult: ...
