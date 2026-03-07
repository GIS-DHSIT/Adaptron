"""Experiment runner that orchestrates the autonomous research loop."""

from __future__ import annotations

import inspect
import logging
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.research.agent import ExperimentAgent
from adaptron.research.config import (
    ExperimentProposal,
    ExperimentResult,
    ResearchConfig,
)
from adaptron.research.timer import TimeBudgetWrapper
from adaptron.research.tracker import ExperimentTracker
from adaptron.train.models import TrainConfig, TrainResult

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Orchestrates the experiment loop: propose, validate, train, evaluate, log."""

    def __init__(
        self,
        config: ResearchConfig,
        output_dir: str | Path,
        event_bus: EventBus | None = None,
    ) -> None:
        self.config = config
        self._output_dir = Path(output_dir)
        self._event_bus = event_bus or EventBus()
        self._research_dir = self._output_dir / "research"
        self.tracker = ExperimentTracker(self._research_dir)
        self._agent = ExperimentAgent(config=config)
        self._trainer = self._load_trainer()
        self._timer = TimeBudgetWrapper(config.time_budget)
        self._best_val_bpb: float | None = None
        self._current_config: TrainConfig = config.base_config

    def _load_trainer(self) -> Any:
        """Try to load trainer from registry; return None if unavailable."""
        try:
            from adaptron.core.registry import global_registry

            trainer_cls = global_registry.get("trainer", self.config.trainer_plugin)
            return trainer_cls()
        except (KeyError, ImportError):
            logger.info(
                "Trainer plugin '%s' not found in registry, "
                "must be injected before run()",
                self.config.trainer_plugin,
            )
            return None

    @staticmethod
    def _config_snapshot(config: Any) -> dict[str, Any]:
        """Convert a config to a dict, handling both dataclass and dict inputs."""
        if is_dataclass(config) and not isinstance(config, type):
            return asdict(config)
        if isinstance(config, dict):
            return config
        return {"raw": str(config)}

    def _emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        event = Event(type=event_type, data=data or {})
        self._event_bus.emit(event_type, event)

    async def run(self) -> None:
        """Run the full experiment loop."""
        self._timer.start()
        self._emit("research_start", {"max_experiments": self.config.max_experiments})

        history: list[ExperimentResult] = []

        for i in range(self.config.max_experiments):
            if self._timer.is_expired():
                logger.info("Time budget expired, stopping research loop")
                break

            result = await self._run_single(i, history)
            history.append(result)

        self._emit(
            "research_complete",
            {
                "total_experiments": len(history),
                "summary": self.tracker.summary(),
            },
        )

    async def _run_single(
        self, index: int, history: list[ExperimentResult]
    ) -> ExperimentResult:
        """Run a single experiment iteration."""
        proposal = await self._agent.propose(self._current_config, history)
        self._emit(
            "experiment_start",
            {"experiment_id": proposal.experiment_id, "index": index},
        )

        # Validate
        errors = self._agent.validate_proposal(proposal.config_changes)
        if inspect.isawaitable(errors):
            errors = await errors
        if errors:
            logger.warning(
                "Proposal %s has validation errors: %s",
                proposal.experiment_id,
                errors,
            )

        # Apply changes
        trial_config = self._agent.apply_changes(
            self._current_config, proposal.config_changes
        )
        if inspect.isawaitable(trial_config):
            trial_config = await trial_config

        # Train
        start_time = time.monotonic()
        try:
            train_result: TrainResult = await self._trainer.train(
                trial_config, None, event_bus=self._event_bus
            )
            training_time = time.monotonic() - start_time

            # Use final_loss as proxy for val_bpb when val_bpb is not available
            val_bpb = train_result.final_loss

            # Determine status
            is_baseline = index == 0
            if is_baseline:
                status = "baseline"
                self._best_val_bpb = val_bpb
                self._current_config = trial_config
            elif self._best_val_bpb is not None and val_bpb < self._best_val_bpb:
                status = "improved"
                previous_best = self._best_val_bpb
                self._best_val_bpb = val_bpb
                self._current_config = trial_config
                self._emit(
                    "experiment_improved",
                    {
                        "experiment_id": proposal.experiment_id,
                        "val_bpb": val_bpb,
                        "previous_best": previous_best,
                    },
                )
            else:
                status = "regressed"
                self._emit(
                    "experiment_reverted",
                    {
                        "experiment_id": proposal.experiment_id,
                        "val_bpb": val_bpb,
                        "best_val_bpb": self._best_val_bpb,
                    },
                )

            result = ExperimentResult(
                experiment_id=proposal.experiment_id,
                description=proposal.description,
                config_snapshot=self._config_snapshot(trial_config),
                val_bpb=val_bpb,
                training_time_s=training_time,
                total_steps=train_result.total_steps,
                final_loss=train_result.final_loss,
                status=status,
                reasoning=proposal.reasoning,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as exc:
            training_time = time.monotonic() - start_time
            logger.error(
                "Experiment %s failed: %s", proposal.experiment_id, exc
            )
            result = ExperimentResult(
                experiment_id=proposal.experiment_id,
                description=proposal.description,
                config_snapshot=self._config_snapshot(trial_config),
                training_time_s=training_time,
                total_steps=0,
                final_loss=0.0,
                status="failed",
                reasoning=f"Training failed: {exc}",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self._emit(
                "experiment_failed",
                {"experiment_id": proposal.experiment_id, "error": str(exc)},
            )

        self.tracker.log(result)
        self._emit(
            "experiment_complete",
            {"experiment_id": result.experiment_id, "status": result.status},
        )
        return result
