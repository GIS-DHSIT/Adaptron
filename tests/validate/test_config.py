from __future__ import annotations

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import (
    BenchmarkResult,
    ComparisonResult,
    HallucinationResult,
    ReadinessResult,
    ValidationReport,
)


def test_validation_config_defaults():
    config = ValidationConfig(model_path="/tmp/model")
    assert config.test_split_ratio == 0.1
    assert config.comparison_samples == 50
    assert config.consistency_runs == 3
    assert config.hallucination_temperature == 0.7
    assert config.hallucination_runs == 5
    assert config.latency_runs == 20
    assert config.output_dir == "output/validation"


def test_validation_config_custom():
    config = ValidationConfig(
        model_path="/tmp/model",
        test_data_path="/tmp/test.jsonl",
        baseline_model="base-model",
        test_split_ratio=0.2,
        comparison_samples=100,
    )
    assert config.test_data_path == "/tmp/test.jsonl"
    assert config.baseline_model == "base-model"
    assert config.comparison_samples == 100


def test_benchmark_result():
    result = BenchmarkResult(
        task_type="qa",
        metrics={"exact_match": 0.85, "f1": 0.90},
        per_sample=[{"input": "q1", "expected": "a1", "predicted": "a1", "correct": True}],
        grade="A",
    )
    assert result.metrics["f1"] == 0.90
    assert result.grade == "A"


def test_comparison_result():
    result = ComparisonResult(
        wins=30,
        losses=15,
        ties=5,
        improvement_pct={"exact_match": 15.0},
        samples=[],
    )
    assert result.wins == 30
    assert result.improvement_pct["exact_match"] == 15.0


def test_readiness_result():
    result = ReadinessResult(
        latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 350, "tokens_per_sec": 25.0},
        consistency_score=0.92,
        edge_case_results=[],
        format_compliance=1.0,
        checks={"latency": "pass", "consistency": "pass"},
    )
    assert result.consistency_score == 0.92
    assert result.checks["latency"] == "pass"


def test_hallucination_result():
    result = HallucinationResult(
        mode="both",
        faithfulness_score=0.88,
        consistency_score=0.91,
        hallucination_rate=0.12,
        flagged_samples=[],
    )
    assert result.hallucination_rate == 0.12
    assert result.mode == "both"


def test_validation_report():
    report = ValidationReport(
        model_info={"name": "test-model", "base_model": "base", "training_mode": "qlora"},
        benchmark=BenchmarkResult(task_type="qa", metrics={}, per_sample=[], grade="B"),
        comparison=None,
        readiness=ReadinessResult(
            latency={},
            consistency_score=0.9,
            edge_case_results=[],
            format_compliance=1.0,
            checks={},
        ),
        hallucination=HallucinationResult(
            mode="self_consistency",
            faithfulness_score=None,
            consistency_score=0.9,
            hallucination_rate=0.1,
            flagged_samples=[],
        ),
        overall_grade="B",
        summary="Model passes validation.",
        timestamp="2026-03-08T00:00:00",
    )
    assert report.overall_grade == "B"
    assert report.comparison is None
