"""Pipeline orchestrator that runs stages sequentially with event reporting."""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from adaptron.core.events import Event, EventBus

logger = logging.getLogger(__name__)


class StageStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    status: StageStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class PipelineResult:
    status: StageStatus
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    total_duration: float = 0.0


class PipelineOrchestrator:
    def __init__(self, bus: EventBus | None = None) -> None:
        self._stages: list[tuple[str, Any]] = []
        self._bus = bus or EventBus()

    def add_stage(self, name: str, stage: Any) -> None:
        self._stages.append((name, stage))

    async def execute(self, context: dict | None = None) -> PipelineResult:
        context = context if context is not None else {}
        result = PipelineResult(status=StageStatus.RUNNING)
        start = time.time()

        self._bus.emit("pipeline_start", Event(
            type="pipeline_start",
            data={"stages": [name for name, _ in self._stages]},
        ))

        for name, stage in self._stages:
            self._bus.emit("stage_start", Event(type="stage_start", data={"stage": name}))
            stage_start = time.time()
            try:
                stage_result = await stage.run(context)
                stage_result.duration_seconds = time.time() - stage_start
                result.stage_results[name] = stage_result
                self._bus.emit("stage_complete", Event(
                    type="stage_complete",
                    data={"stage": name, "status": stage_result.status.value},
                ))
            except Exception as exc:
                stage_result = StageResult(
                    status=StageStatus.FAILED, error=str(exc),
                    duration_seconds=time.time() - stage_start,
                )
                result.stage_results[name] = stage_result
                self._bus.emit("stage_error", Event(
                    type="stage_error", data={"stage": name, "error": str(exc)},
                ))
                logger.error("Stage '%s' failed: %s", name, exc)
                result.status = StageStatus.FAILED
                result.total_duration = time.time() - start
                self._bus.emit("pipeline_complete", Event(
                    type="pipeline_complete", data={"status": "failed", "failed_stage": name},
                ))
                return result

        result.status = StageStatus.COMPLETED
        result.total_duration = time.time() - start
        self._bus.emit("pipeline_complete", Event(
            type="pipeline_complete", data={"status": "completed"},
        ))
        return result
