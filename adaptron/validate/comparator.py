from __future__ import annotations

from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import ComparisonResult, ComparisonSample


class ModelComparator:
    """Compare baseline and fine-tuned model outputs."""

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self.config = config or ValidationConfig(model_path="")

    def compute_wins(
        self,
        baseline_preds: list[str],
        finetuned_preds: list[str],
        references: list[str],
    ) -> tuple[int, int, int]:
        """Return (wins, losses, ties) for finetuned vs baseline."""
        wins = losses = ties = 0
        for bp, fp, ref in zip(baseline_preds, finetuned_preds, references):
            b_correct = bp.strip().lower() == ref.strip().lower()
            f_correct = fp.strip().lower() == ref.strip().lower()
            if f_correct and not b_correct:
                wins += 1
            elif b_correct and not f_correct:
                losses += 1
            else:
                ties += 1
        return wins, losses, ties

    def compute_improvement(
        self,
        baseline_metrics: dict[str, float],
        finetuned_metrics: dict[str, float],
    ) -> dict[str, float]:
        """Compute percentage change per metric."""
        improvement: dict[str, float] = {}
        for key in finetuned_metrics:
            if key in baseline_metrics and baseline_metrics[key] != 0:
                pct = ((finetuned_metrics[key] - baseline_metrics[key]) / baseline_metrics[key]) * 100.0
                improvement[key] = round(pct, 2)
            elif key in baseline_metrics and baseline_metrics[key] == 0:
                improvement[key] = float("inf") if finetuned_metrics[key] > 0 else 0.0
        return improvement

    def build_samples(
        self,
        prompts: list[str],
        baseline_preds: list[str],
        finetuned_preds: list[str],
        references: list[str],
    ) -> list[ComparisonSample]:
        """Build comparison samples with winner determination."""
        samples: list[ComparisonSample] = []
        for prompt, bp, fp, ref in zip(prompts, baseline_preds, finetuned_preds, references):
            b_correct = bp.strip().lower() == ref.strip().lower()
            f_correct = fp.strip().lower() == ref.strip().lower()
            if f_correct and not b_correct:
                winner = "finetuned"
            elif b_correct and not f_correct:
                winner = "baseline"
            else:
                winner = "tie"
            samples.append(ComparisonSample(
                prompt=prompt,
                baseline_response=bp,
                finetuned_response=fp,
                reference=ref,
                winner=winner,
            ))
        return samples

    def run(
        self,
        prompts: list[str],
        baseline_preds: list[str],
        finetuned_preds: list[str],
        references: list[str],
        baseline_metrics: dict[str, float] | None = None,
        finetuned_metrics: dict[str, float] | None = None,
    ) -> ComparisonResult:
        """Run full comparison and return result."""
        wins, losses, ties = self.compute_wins(baseline_preds, finetuned_preds, references)
        improvement: dict[str, float] = {}
        if baseline_metrics and finetuned_metrics:
            improvement = self.compute_improvement(baseline_metrics, finetuned_metrics)
        samples = self.build_samples(prompts, baseline_preds, finetuned_preds, references)
        return ComparisonResult(
            wins=wins,
            losses=losses,
            ties=ties,
            improvement_pct=improvement,
            samples=samples,
        )
