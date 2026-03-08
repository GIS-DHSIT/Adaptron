from __future__ import annotations

from adaptron.validate.benchmark import BenchmarkSuite


def test_detect_task_type_qa():
    suite = BenchmarkSuite()
    data = [
        {"response": "The capital of France is Paris, which is a large city."},
        {"response": "Berlin is the capital and largest city of Germany."},
    ]
    assert suite.detect_task_type(data) == "qa"


def test_detect_task_type_classification():
    suite = BenchmarkSuite()
    data = [
        {"response": "positive"},
        {"response": "negative"},
        {"response": "neutral"},
    ]
    assert suite.detect_task_type(data) == "classification"


def test_compute_qa_metrics():
    suite = BenchmarkSuite()
    predictions = ["Paris", "Berlin", "wrong"]
    references = ["Paris", "Berlin", "London"]
    metrics = suite.compute_metrics(predictions, references, "qa")
    assert abs(metrics["exact_match"] - 2 / 3) < 1e-6
    assert metrics["f1"] > 0.6  # 2 perfect + partial


def test_compute_classification_metrics():
    suite = BenchmarkSuite()
    predictions = ["positive", "negative", "positive", "neutral"]
    references = ["positive", "negative", "negative", "neutral"]
    metrics = suite.compute_metrics(predictions, references, "classification")
    assert metrics["accuracy"] == 0.75


def test_grade_metrics():
    suite = BenchmarkSuite()
    metrics = {"exact_match": 0.85, "f1": 0.90}
    grade = suite.grade_metrics(metrics)
    assert grade == "A"


def test_grade_metrics_failing():
    suite = BenchmarkSuite()
    metrics = {"exact_match": 0.3, "f1": 0.4}
    grade = suite.grade_metrics(metrics)
    assert grade in ("D", "F")
