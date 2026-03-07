from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.evaluate.base import BaseEvaluator


@register_plugin("evaluator", "domain")
class DomainEvaluator(BaseEvaluator):
    def exact_match(
        self, predictions: list[str], references: list[str]
    ) -> float:
        if not predictions:
            return 0.0
        matches = sum(
            1
            for p, r in zip(predictions, references)
            if p.strip().lower() == r.strip().lower()
        )
        return matches / len(predictions)

    def evaluate(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, Any]:
        em = self.exact_match(predictions, references)
        return {
            "exact_match": em,
            "total_samples": len(predictions),
            "correct": int(em * len(predictions)),
        }
