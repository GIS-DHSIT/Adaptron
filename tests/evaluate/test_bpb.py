import math

from adaptron.evaluate.bpb import BPBEvaluator


def test_bpb_evaluator_registered():
    from adaptron.core.registry import global_registry

    plugin = global_registry.get("evaluator", "bpb")
    assert plugin is BPBEvaluator


def test_compute_bpb_from_losses():
    evaluator = BPBEvaluator()
    token_losses_nats = [1.0, 2.0, 1.5]
    total_bytes = 10
    bpb = evaluator.compute_bpb(token_losses_nats, total_bytes)
    expected = sum(token_losses_nats) / (math.log(2) * total_bytes)
    assert abs(bpb - expected) < 1e-6


def test_compute_bpb_zero_bytes():
    evaluator = BPBEvaluator()
    bpb = evaluator.compute_bpb([1.0, 2.0], 0)
    assert bpb == float("inf")


def test_evaluate_returns_dict():
    evaluator = BPBEvaluator()
    result = evaluator.evaluate(predictions=["Hello world"], references=["Hello world"])
    assert "info" in result
