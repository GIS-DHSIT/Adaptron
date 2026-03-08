from __future__ import annotations

from collections import Counter
from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import BenchmarkResult


class BenchmarkSuite:
    """Runs benchmark evaluation on model predictions."""

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self.config = config or ValidationConfig(model_path="")

    def detect_task_type(self, data: list[dict[str, Any]]) -> str:
        """Detect task type based on average response length."""
        if not data:
            return "qa"
        avg_len = sum(len(str(d.get("response", ""))) for d in data) / len(data)
        return "classification" if avg_len < 20 else "qa"

    def compute_metrics(
        self,
        predictions: list[str],
        references: list[str],
        task_type: str,
    ) -> dict[str, float]:
        """Dispatch to task-specific metric computation."""
        if task_type == "classification":
            return self._classification_metrics(predictions, references)
        return self._qa_metrics(predictions, references)

    def _qa_metrics(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, float]:
        """Compute exact match and token-level F1 for QA tasks."""
        if not predictions:
            return {"exact_match": 0.0, "f1": 0.0}
        exact_matches = sum(
            1 for p, r in zip(predictions, references) if p.strip().lower() == r.strip().lower()
        )
        exact_match = exact_matches / len(predictions)
        f1_scores = [self._token_f1(p, r) for p, r in zip(predictions, references)]
        avg_f1 = sum(f1_scores) / len(f1_scores)
        return {"exact_match": exact_match, "f1": avg_f1}

    def _token_f1(self, prediction: str, reference: str) -> float:
        """Compute token-level F1 using Counter intersection."""
        pred_tokens = Counter(prediction.lower().split())
        ref_tokens = Counter(reference.lower().split())
        if not pred_tokens and not ref_tokens:
            return 1.0
        if not pred_tokens or not ref_tokens:
            return 0.0
        common = sum((pred_tokens & ref_tokens).values())
        if common == 0:
            return 0.0
        precision = common / sum(pred_tokens.values())
        recall = common / sum(ref_tokens.values())
        return 2 * precision * recall / (precision + recall)

    def _classification_metrics(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, float]:
        """Compute accuracy, macro precision, recall, and F1 for classification."""
        if not predictions:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}
        correct = sum(1 for p, r in zip(predictions, references) if p.strip().lower() == r.strip().lower())
        accuracy = correct / len(predictions)

        labels = sorted(set(r.strip().lower() for r in references))
        precisions = []
        recalls = []
        for label in labels:
            tp = sum(
                1
                for p, r in zip(predictions, references)
                if p.strip().lower() == label and r.strip().lower() == label
            )
            fp = sum(
                1
                for p, r in zip(predictions, references)
                if p.strip().lower() == label and r.strip().lower() != label
            )
            fn = sum(
                1
                for p, r in zip(predictions, references)
                if p.strip().lower() != label and r.strip().lower() == label
            )
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            precisions.append(prec)
            recalls.append(rec)

        macro_prec = sum(precisions) / len(labels) if labels else 0.0
        macro_rec = sum(recalls) / len(labels) if labels else 0.0
        macro_f1 = (
            2 * macro_prec * macro_rec / (macro_prec + macro_rec)
            if (macro_prec + macro_rec) > 0
            else 0.0
        )
        return {
            "accuracy": accuracy,
            "precision": macro_prec,
            "recall": macro_rec,
            "f1": macro_f1,
        }

    def grade_metrics(self, metrics: dict[str, float]) -> str:
        """Assign a letter grade based on thresholds."""
        thresholds = self.config.thresholds
        scores: list[str] = []
        for metric_name, value in metrics.items():
            if metric_name in thresholds:
                t = thresholds[metric_name]
                if value >= t["pass"]:
                    scores.append("A")
                elif value >= t["warning"]:
                    scores.append("C")
                else:
                    scores.append("F")
        if not scores:
            # Fallback: use primary metric value
            avg = sum(metrics.values()) / len(metrics) if metrics else 0.0
            if avg >= 0.8:
                return "A"
            elif avg >= 0.6:
                return "B"
            elif avg >= 0.4:
                return "C"
            elif avg >= 0.2:
                return "D"
            return "F"

        # Worst grade wins
        grade_order = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        return min(scores, key=lambda g: grade_order.get(g, 0))

    def run(
        self,
        predictions: list[str],
        references: list[str],
        test_data: list[dict[str, Any]] | None = None,
    ) -> BenchmarkResult:
        """Run the full benchmark suite."""
        task_type = self.config.task_type
        if task_type is None and test_data:
            task_type = self.detect_task_type(test_data)
        task_type = task_type or "qa"

        metrics = self.compute_metrics(predictions, references, task_type)
        grade = self.grade_metrics(metrics)

        per_sample = []
        for i, (p, r) in enumerate(zip(predictions, references)):
            per_sample.append({
                "index": i,
                "prediction": p,
                "reference": r,
                "correct": p.strip().lower() == r.strip().lower(),
            })

        return BenchmarkResult(
            task_type=task_type,
            metrics=metrics,
            per_sample=per_sample,
            grade=grade,
        )
