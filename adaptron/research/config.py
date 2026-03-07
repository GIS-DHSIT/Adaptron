from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adaptron.train.models import TrainConfig


@dataclass
class ResearchConfig:
    base_config: TrainConfig
    time_budget: int = 300
    max_experiments: int = 50
    max_total_time: int | None = None
    eval_tokens: int = 20_971_520
    mode: str = "config"
    strategy: str = "explore_exploit"
    trainer_plugin: str = "qlora"
    agent_model: str = "claude-sonnet-4-20250514"


@dataclass
class ExperimentProposal:
    experiment_id: str
    description: str
    config_changes: dict[str, Any]
    reasoning: str
    code_changes: str | None = None
    parent_id: str | None = None


@dataclass
class ExperimentResult:
    experiment_id: str
    description: str
    config_snapshot: dict[str, Any]
    training_time_s: float
    total_steps: int
    final_loss: float
    status: str
    reasoning: str
    timestamp: str
    parent_id: str | None = None
    val_bpb: float | None = None
    val_loss: float | None = None
    domain_score: float | None = None
