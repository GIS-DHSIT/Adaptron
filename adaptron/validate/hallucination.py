from __future__ import annotations

from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import HallucinationResult


class HallucinationDetector:
    """Detect hallucinations using faithfulness and self-consistency checks."""

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self.config = config or ValidationConfig(model_path="")

    def _token_overlap(self, text_a: str, text_b: str) -> float:
        """Compute Jaccard similarity on tokens."""
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a and not tokens_b:
            return 1.0
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def compute_faithfulness(
        self, predictions: list[str], references: list[str]
    ) -> float:
        """Compute average token overlap between predictions and references."""
        if not predictions:
            return 0.0
        scores = [
            self._token_overlap(p, r) for p, r in zip(predictions, references)
        ]
        return sum(scores) / len(scores)

    def compute_self_consistency(
        self, responses_per_prompt: list[list[str]]
    ) -> float:
        """Compute average pairwise token overlap across response sets."""
        if not responses_per_prompt:
            return 1.0
        scores: list[float] = []
        for responses in responses_per_prompt:
            if len(responses) < 2:
                scores.append(1.0)
                continue
            pair_scores: list[float] = []
            for i in range(len(responses)):
                for j in range(i + 1, len(responses)):
                    pair_scores.append(self._token_overlap(responses[i], responses[j]))
            scores.append(sum(pair_scores) / len(pair_scores) if pair_scores else 1.0)
        return sum(scores) / len(scores)

    def compute_hallucination_rate(
        self,
        predictions: list[str],
        references: list[str],
        threshold: float = 0.5,
    ) -> tuple[float, list[dict[str, Any]]]:
        """Compute hallucination rate and return flagged samples."""
        if not predictions:
            return 0.0, []
        flagged: list[dict[str, Any]] = []
        for i, (p, r) in enumerate(zip(predictions, references)):
            overlap = self._token_overlap(p, r)
            if overlap < threshold:
                flagged.append({
                    "index": i,
                    "prediction": p,
                    "reference": r,
                    "overlap": round(overlap, 4),
                })
        rate = len(flagged) / len(predictions)
        return rate, flagged

    def run(
        self,
        predictions: list[str] | None = None,
        references: list[str] | None = None,
        responses_per_prompt: list[list[str]] | None = None,
        threshold: float = 0.5,
    ) -> HallucinationResult:
        """Run hallucination detection with mode selection."""
        has_refs = predictions is not None and references is not None
        has_consistency = responses_per_prompt is not None

        if has_refs and has_consistency:
            mode = "both"
        elif has_refs:
            mode = "reference"
        elif has_consistency:
            mode = "self_consistency"
        else:
            mode = "none"

        faithfulness: float | None = None
        consistency: float | None = None
        rate = 0.0
        flagged: list[dict[str, Any]] = []

        if has_refs:
            faithfulness = self.compute_faithfulness(predictions, references)  # type: ignore[arg-type]
            rate, flagged = self.compute_hallucination_rate(
                predictions, references, threshold  # type: ignore[arg-type]
            )

        if has_consistency:
            consistency = self.compute_self_consistency(responses_per_prompt)  # type: ignore[arg-type]

        return HallucinationResult(
            mode=mode,
            faithfulness_score=faithfulness,
            consistency_score=consistency,
            hallucination_rate=rate,
            flagged_samples=flagged,
        )
