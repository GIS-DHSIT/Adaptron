from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    task_type: str
    metrics: dict[str, float]
    per_sample: list[dict[str, Any]]
    grade: str


@dataclass
class ComparisonSample:
    prompt: str
    baseline_response: str
    finetuned_response: str
    reference: str | None = None
    winner: str = ""


@dataclass
class ComparisonResult:
    wins: int
    losses: int
    ties: int
    improvement_pct: dict[str, float]
    samples: list[ComparisonSample | dict[str, Any]]
    latency_baseline: dict[str, float] = field(default_factory=dict)
    latency_finetuned: dict[str, float] = field(default_factory=dict)


@dataclass
class ReadinessResult:
    latency: dict[str, float]
    consistency_score: float
    edge_case_results: list[dict[str, Any]]
    format_compliance: float
    checks: dict[str, str]
    memory_mb: float | None = None


@dataclass
class HallucinationResult:
    mode: str
    faithfulness_score: float | None
    consistency_score: float | None
    hallucination_rate: float
    flagged_samples: list[dict[str, Any]]


@dataclass
class ValidationReport:
    model_info: dict[str, Any]
    benchmark: BenchmarkResult | None
    comparison: ComparisonResult | None
    readiness: ReadinessResult | None
    hallucination: HallucinationResult | None
    overall_grade: str
    summary: str
    timestamp: str
