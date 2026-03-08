from __future__ import annotations

from adaptron.validate.readiness import ProductionReadiness


def test_compute_latency_stats():
    pr = ProductionReadiness()
    durations = [100, 120, 130, 150, 200, 250, 300, 350, 400, 500]
    stats = pr.compute_latency_stats(durations)
    assert stats["p50_ms"] <= stats["p95_ms"] <= stats["p99_ms"]
    assert stats["mean_ms"] > 0


def test_check_consistency_high():
    pr = ProductionReadiness()
    responses = [
        ["Paris", "Paris", "Paris"],
        ["Berlin", "Berlin", "Berlin"],
    ]
    score = pr.check_consistency(responses)
    assert score == 1.0


def test_check_consistency_low():
    pr = ProductionReadiness()
    responses = [
        ["Paris", "London", "Berlin"],
    ]
    score = pr.check_consistency(responses)
    assert score < 1.0


def test_check_format_compliance():
    pr = ProductionReadiness()
    formats = ["json", "text"]
    outputs = ['{"key": "value"}', "Hello world"]
    score = pr.check_format_compliance(formats, outputs)
    assert score == 1.0


def test_check_format_compliance_partial():
    pr = ProductionReadiness()
    formats = ["json", "json"]
    outputs = ['{"key": "value"}', "not json at all"]
    score = pr.check_format_compliance(formats, outputs)
    assert score == 0.5
