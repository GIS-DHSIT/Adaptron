from __future__ import annotations

import math
from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.evaluate.base import BaseEvaluator


@register_plugin("evaluator", "bpb")
class BPBEvaluator(BaseEvaluator):
    """Bits-per-byte evaluator -- vocab-size independent metric."""

    def compute_bpb(self, token_losses_nats: list[float], total_bytes: int) -> float:
        if total_bytes == 0:
            return float("inf")
        total_nats = sum(token_losses_nats)
        return total_nats / (math.log(2) * total_bytes)

    def evaluate(self, predictions: list[str], references: list[str]) -> dict[str, Any]:
        return {
            "info": "BPB evaluation requires model and tokenizer. Use compute_bpb() directly.",
            "total_samples": len(predictions),
        }
