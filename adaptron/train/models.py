from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrainConfig:
    base_model: str
    output_dir: str
    training_mode: str = "qlora"
    epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4
    max_seq_length: int = 2048
    lora_rank: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    gradient_accumulation_steps: int = 4
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    use_4bit: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainResult:
    model_path: str
    adapter_path: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    training_mode: str = ""
    base_model: str = ""
    total_steps: int = 0
    final_loss: float = 0.0
