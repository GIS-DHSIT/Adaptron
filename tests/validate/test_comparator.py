from __future__ import annotations

from adaptron.validate.comparator import ModelComparator


def test_compute_wins_losses():
    comp = ModelComparator()
    baseline = ["Paris", "wrong", "Tokyo"]
    finetuned = ["Paris", "Berlin", "Tokyo"]
    refs = ["Paris", "Berlin", "Tokyo"]
    wins, losses, ties = comp.compute_wins(baseline, finetuned, refs)
    assert wins == 1
    assert losses == 0
    assert ties == 2


def test_compute_improvement():
    comp = ModelComparator()
    baseline_metrics = {"exact_match": 0.60}
    finetuned_metrics = {"exact_match": 0.80}
    improvement = comp.compute_improvement(baseline_metrics, finetuned_metrics)
    assert abs(improvement["exact_match"] - 33.33) < 0.1


def test_build_samples():
    comp = ModelComparator()
    prompts = ["What is the capital of Germany?"]
    baseline = ["Munich"]
    finetuned = ["Berlin"]
    refs = ["Berlin"]
    samples = comp.build_samples(prompts, baseline, finetuned, refs)
    assert len(samples) == 1
    assert samples[0].winner == "finetuned"
