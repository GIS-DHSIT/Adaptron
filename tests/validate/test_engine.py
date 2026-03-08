from adaptron.validate.engine import ValidationEngine
from adaptron.validate.config import ValidationConfig

def test_engine_compute_overall_grade_all_pass():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    grade = engine.compute_overall_grade(benchmark_grade="A", hallucination_rate=0.03, improvement_pct=25.0)
    assert grade == "A"

def test_engine_compute_overall_grade_some_warnings():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    grade = engine.compute_overall_grade(benchmark_grade="C", hallucination_rate=0.08, improvement_pct=10.0)
    assert grade == "C"

def test_engine_compute_overall_grade_failing():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    grade = engine.compute_overall_grade(benchmark_grade="F", hallucination_rate=0.35, improvement_pct=-5.0)
    assert grade == "F"

def test_engine_generate_summary():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    summary = engine.generate_summary(overall_grade="B", benchmark_grade="B",
        hallucination_rate=0.08, improvement_pct=15.0)
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "B" in summary
