import json
from pathlib import Path
from adaptron.validate.report import ReportGenerator
from adaptron.validate.models import (
    BenchmarkResult, ReadinessResult, HallucinationResult, ValidationReport,
)

def _make_report() -> ValidationReport:
    return ValidationReport(
        model_info={"name": "test-model", "base_model": "base", "training_mode": "qlora"},
        benchmark=BenchmarkResult(task_type="qa",
            metrics={"exact_match": 0.85, "f1": 0.90},
            per_sample=[{"index": 0, "correct": True}], grade="A"),
        comparison=None,
        readiness=ReadinessResult(
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 150},
            consistency_score=0.92, edge_case_results=[], format_compliance=1.0,
            checks={"latency": "pass", "consistency": "pass"}),
        hallucination=HallucinationResult(mode="reference", faithfulness_score=0.95,
            consistency_score=None, hallucination_rate=0.05, flagged_samples=[]),
        overall_grade="A", summary="Model passes all validation checks.",
        timestamp="2026-03-08T00:00:00")

def test_generate_json(tmp_path):
    gen = ReportGenerator(output_dir=str(tmp_path))
    report = _make_report()
    json_path = gen.generate_json(report)
    assert Path(json_path).exists()
    data = json.loads(Path(json_path).read_text())
    assert data["overall_grade"] == "A"
    assert data["benchmark"]["metrics"]["exact_match"] == 0.85

def test_generate_html(tmp_path):
    gen = ReportGenerator(output_dir=str(tmp_path))
    report = _make_report()
    html_path = gen.generate_html(report)
    assert Path(html_path).exists()
    content = Path(html_path).read_text()
    assert "test-model" in content
    assert "Grade: A" in content

def test_generate_both(tmp_path):
    gen = ReportGenerator(output_dir=str(tmp_path))
    report = _make_report()
    json_path, html_path = gen.generate(report)
    assert Path(json_path).exists()
    assert Path(html_path).exists()
