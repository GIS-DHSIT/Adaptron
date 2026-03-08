from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationConfig:
    model_path: str
    test_data_path: str | None = None
    baseline_model: str | None = None
    task_type: str | None = None
    test_split_ratio: float = 0.1
    comparison_samples: int = 50
    consistency_runs: int = 3
    hallucination_temperature: float = 0.7
    hallucination_runs: int = 5
    latency_runs: int = 20
    per_sample_timeout: float = 30.0
    output_dir: str = "output/validation"
    thresholds: dict[str, Any] = field(default_factory=lambda: {
        "exact_match": {"pass": 0.8, "warning": 0.6},
        "f1": {"pass": 0.75, "warning": 0.5},
        "consistency": {"pass": 0.85, "warning": 0.7},
        "hallucination_rate": {"pass": 0.05, "warning": 0.15},
        "improvement_pct": {"pass": 20.0, "warning": 5.0},
    })
