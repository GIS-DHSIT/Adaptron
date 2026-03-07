"""Pipeline configuration and wizard-to-config translation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WizardAnswers:
    primary_goal: str
    data_sources: list[str]
    data_freshness: str
    hardware: str
    timeline: str
    accuracy: str
    model_size: str


@dataclass
class PipelineConfig:
    primary_goal: str = ""
    data_sources: list[str] = field(default_factory=list)
    data_freshness: str = ""
    hardware: str = ""
    timeline: str = ""
    accuracy: str = ""
    model_size: str = ""
    training_modes: list[str] = field(default_factory=list)
    base_model: str = ""
    deploy_targets: list[str] = field(default_factory=lambda: ["gguf", "ollama"])
    custom_base_model: str | None = None
    lora_rank: int = 64
    epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4
    max_seq_length: int = 2048
    quantization: str = "Q4_K_M"

    @classmethod
    def from_wizard(cls, answers: WizardAnswers) -> PipelineConfig:
        config = cls(
            primary_goal=answers.primary_goal,
            data_sources=answers.data_sources,
            data_freshness=answers.data_freshness,
            hardware=answers.hardware,
            timeline=answers.timeline,
            accuracy=answers.accuracy,
            model_size=answers.model_size,
        )
        config.training_modes = _compute_training_modes(answers)
        config.base_model = _select_base_model(answers)
        return config

    @classmethod
    def from_yaml(cls, path: Path) -> PipelineConfig:
        with open(path) as f:
            data = yaml.safe_load(f)
        wizard_data = data.get("wizard", {})
        overrides = data.get("overrides", {})
        if wizard_data:
            answers = WizardAnswers(**wizard_data)
            config = cls.from_wizard(answers)
        else:
            config = cls()
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

    def to_yaml(self, path: Path) -> None:
        data = {
            "wizard": {
                "primary_goal": self.primary_goal,
                "data_sources": self.data_sources,
                "data_freshness": self.data_freshness,
                "hardware": self.hardware,
                "timeline": self.timeline,
                "accuracy": self.accuracy,
                "model_size": self.model_size,
            },
            "overrides": {
                "epochs": self.epochs,
                "learning_rate": self.learning_rate,
                "batch_size": self.batch_size,
                "lora_rank": self.lora_rank,
                "max_seq_length": self.max_seq_length,
                "quantization": self.quantization,
            },
        }
        if self.custom_base_model:
            data["overrides"]["custom_base_model"] = self.custom_base_model
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _compute_training_modes(answers: WizardAnswers) -> list[str]:
    scores: dict[str, int] = {"qlora": 0, "cpt": 0, "distill": 0, "rag": 0}
    goal = answers.primary_goal
    if goal == "qa_docs":
        scores["qlora"] += 3
        scores["rag"] += 2
    elif goal == "erp_edw":
        scores["rag"] += 4
        scores["qlora"] += 1
    elif goal == "report_gen":
        scores["qlora"] += 4
        scores["distill"] += 2
    elif goal == "specialist":
        scores["cpt"] += 4
        scores["qlora"] += 2
    if "erp" in answers.data_sources or "edw" in answers.data_sources:
        scores["rag"] += 3
    if answers.data_sources == ["docs"]:
        scores["qlora"] += 2
    if len(answers.data_sources) >= 3:
        scores["rag"] += 2
    if answers.data_freshness == "static":
        scores["qlora"] += 3
        scores["cpt"] += 2
    elif answers.data_freshness == "monthly":
        scores["qlora"] += 1
        scores["rag"] += 2
    elif answers.data_freshness in ("daily", "realtime"):
        scores["rag"] += 5
        scores["qlora"] -= 2
    if answers.hardware == "low":
        scores["cpt"] -= 5
        scores["distill"] += 2
    elif answers.hardware in ("high", "cloud"):
        scores["cpt"] += 3
    if answers.timeline == "fast":
        scores["cpt"] -= 5
        scores["distill"] -= 2
    elif answers.timeline in ("long", "unlimited"):
        scores["cpt"] += 2
    if answers.accuracy == "enterprise":
        scores["qlora"] += 2
        scores["rag"] += 3
    elif answers.accuracy == "mission":
        scores["rag"] += 5
        scores["cpt"] += 2
    if answers.model_size == "tiny":
        scores["distill"] += 4
        scores["cpt"] -= 3
    elif answers.model_size == "small":
        scores["qlora"] += 2
    elif answers.model_size == "large":
        scores["cpt"] += 2
    modes = [k for k, v in sorted(scores.items(), key=lambda x: -x[1]) if v > 0]
    return modes if modes else ["qlora"]


def _select_base_model(answers: WizardAnswers) -> str:
    if answers.hardware == "low" and answers.model_size in ("medium", "large"):
        return "microsoft/phi-3.5-mini-instruct"
    models = {
        "tiny": "microsoft/phi-3.5-mini-instruct",
        "small": "Qwen/Qwen2.5-7B-Instruct",
        "medium": "Qwen/Qwen2.5-14B-Instruct",
        "large": "Qwen/Qwen2.5-32B-Instruct",
    }
    return models.get(answers.model_size, "Qwen/Qwen2.5-7B-Instruct")
