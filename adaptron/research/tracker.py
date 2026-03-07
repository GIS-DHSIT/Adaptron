from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from adaptron.research.config import ExperimentResult

TSV_FIELDS = [
    "experiment_id",
    "parent_id",
    "description",
    "val_bpb",
    "val_loss",
    "domain_score",
    "final_loss",
    "total_steps",
    "training_time_s",
    "status",
    "reasoning",
    "timestamp",
]


class ExperimentTracker:
    """Tracks experiments in a TSV file for persistence and resume."""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._tsv_path = self._output_dir / "experiments.tsv"
        self._results: list[dict[str, str]] = []
        self._load()

    def _load(self) -> None:
        if self._tsv_path.exists():
            with open(self._tsv_path, "r", newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                self._results = list(reader)

    def log(self, result: ExperimentResult) -> None:
        row: dict[str, str] = {}
        for field in TSV_FIELDS:
            value = getattr(result, field, None)
            row[field] = "" if value is None else str(value)
        self._results.append(row)
        self._write_tsv()

    def _write_tsv(self) -> None:
        with open(self._tsv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=TSV_FIELDS, delimiter="\t")
            writer.writeheader()
            writer.writerows(self._results)

    def list_results(self) -> list[dict[str, str]]:
        return list(self._results)

    def get_best(self) -> dict[str, str] | None:
        valid = [r for r in self._results if r.get("val_bpb") not in ("", None)]
        if not valid:
            return None
        return min(valid, key=lambda r: float(r["val_bpb"]))

    def summary(self) -> dict[str, Any]:
        total = len(self._results)
        improvements = sum(1 for r in self._results if r.get("status") == "improved")
        regressions = sum(1 for r in self._results if r.get("status") == "regressed")
        failures = sum(1 for r in self._results if r.get("status") == "failed")
        best = self.get_best()
        best_val_bpb = float(best["val_bpb"]) if best else None
        best_experiment_id = best["experiment_id"] if best else None
        return {
            "total_experiments": total,
            "improvements": improvements,
            "regressions": regressions,
            "failures": failures,
            "best_val_bpb": best_val_bpb,
            "best_experiment_id": best_experiment_id,
        }
