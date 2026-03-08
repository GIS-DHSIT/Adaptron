from __future__ import annotations

from adaptron.validate.hallucination import HallucinationDetector


def test_reference_faithfulness_perfect():
    det = HallucinationDetector()
    preds = ["The capital of France is Paris"]
    refs = ["The capital of France is Paris"]
    score = det.compute_faithfulness(preds, refs)
    assert score == 1.0


def test_reference_faithfulness_partial():
    det = HallucinationDetector()
    preds = ["capital of Germany"]
    refs = ["capital of France"]
    score = det.compute_faithfulness(preds, refs)
    assert 0.0 < score < 1.0


def test_self_consistency_identical():
    det = HallucinationDetector()
    responses = [
        ["Paris is the capital", "Paris is the capital", "Paris is the capital"],
    ]
    score = det.compute_self_consistency(responses)
    assert score == 1.0


def test_self_consistency_divergent():
    det = HallucinationDetector()
    responses = [
        ["Paris is great", "Tokyo is wonderful", "Berlin is nice"],
    ]
    score = det.compute_self_consistency(responses)
    assert score < 1.0


def test_hallucination_rate():
    det = HallucinationDetector()
    preds = ["Paris", "something completely different xyz", "Tokyo"]
    refs = ["Paris", "Berlin", "Tokyo"]
    rate, flagged = det.compute_hallucination_rate(preds, refs)
    assert abs(rate - 1 / 3) < 1e-6
    assert len(flagged) == 1
    assert flagged[0]["index"] == 1
