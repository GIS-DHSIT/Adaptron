# Model Validation Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Model Validation Framework that proves finetuned models are fit for purpose — automated benchmarks, base-vs-finetuned comparison, production readiness checks, hallucination detection, and dual-format reports (HTML + JSON).

**Architecture:** A shared `ValidationEngine` orchestrates four validator plugins (BenchmarkSuite, ModelComparator, ProductionReadiness, HallucinationDetector), collects results into a `ValidationReport`, and generates HTML + JSON reports via `ReportGenerator`. The engine is wrapped by a pipeline `ValidateStage`, a CLI `validate` command, and API routes.

**Tech Stack:** Python 3.11+, dataclasses, Jinja2 (HTML reports), existing Adaptron plugins (EventBus, registry, PlaygroundEngine).

---

## Phase 1: Data Models & Config

### Task 1: Validation data models and config

**Files:**
- Create: `adaptron/validate/__init__.py`
- Create: `adaptron/validate/models.py`
- Create: `adaptron/validate/config.py`
- Create: `tests/validate/__init__.py`
- Create: `tests/validate/test_config.py`

**Step 1: Write failing tests**

```python
# tests/validate/__init__.py
```

```python
# tests/validate/test_config.py
from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import (
    BenchmarkResult,
    ComparisonResult,
    ReadinessResult,
    HallucinationResult,
    ValidationReport,
)


def test_validation_config_defaults():
    config = ValidationConfig(model_path="/tmp/model")
    assert config.test_split_ratio == 0.1
    assert config.comparison_samples == 50
    assert config.consistency_runs == 3
    assert config.hallucination_temperature == 0.7
    assert config.hallucination_runs == 5
    assert config.latency_runs == 20
    assert config.output_dir == "output/validation"


def test_validation_config_custom():
    config = ValidationConfig(
        model_path="/tmp/model",
        test_data_path="/tmp/test.jsonl",
        baseline_model="base-model",
        test_split_ratio=0.2,
        comparison_samples=100,
    )
    assert config.test_data_path == "/tmp/test.jsonl"
    assert config.baseline_model == "base-model"
    assert config.comparison_samples == 100


def test_benchmark_result():
    result = BenchmarkResult(
        task_type="qa",
        metrics={"exact_match": 0.85, "f1": 0.90},
        per_sample=[{"input": "q1", "expected": "a1", "predicted": "a1", "correct": True}],
        grade="A",
    )
    assert result.metrics["f1"] == 0.90
    assert result.grade == "A"


def test_comparison_result():
    result = ComparisonResult(
        wins=30, losses=15, ties=5,
        improvement_pct={"exact_match": 15.0},
        samples=[],
    )
    assert result.wins == 30
    assert result.improvement_pct["exact_match"] == 15.0


def test_readiness_result():
    result = ReadinessResult(
        latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 350, "tokens_per_sec": 25.0},
        consistency_score=0.92,
        edge_case_results=[],
        format_compliance=1.0,
        checks={"latency": "pass", "consistency": "pass"},
    )
    assert result.consistency_score == 0.92
    assert result.checks["latency"] == "pass"


def test_hallucination_result():
    result = HallucinationResult(
        mode="both",
        faithfulness_score=0.88,
        consistency_score=0.91,
        hallucination_rate=0.12,
        flagged_samples=[],
    )
    assert result.hallucination_rate == 0.12
    assert result.mode == "both"


def test_validation_report():
    report = ValidationReport(
        model_info={"name": "test-model", "base_model": "base", "training_mode": "qlora"},
        benchmark=BenchmarkResult(task_type="qa", metrics={}, per_sample=[], grade="B"),
        comparison=None,
        readiness=ReadinessResult(
            latency={}, consistency_score=0.9, edge_case_results=[],
            format_compliance=1.0, checks={},
        ),
        hallucination=HallucinationResult(
            mode="self_consistency", faithfulness_score=None,
            consistency_score=0.9, hallucination_rate=0.1, flagged_samples=[],
        ),
        overall_grade="B",
        summary="Model passes validation.",
        timestamp="2026-03-08T00:00:00",
    )
    assert report.overall_grade == "B"
    assert report.comparison is None
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# adaptron/validate/__init__.py
"""Model Validation Framework for production readiness verification."""
```

```python
# adaptron/validate/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkResult:
    task_type: str
    metrics: dict[str, float]
    per_sample: list[dict[str, Any]]
    grade: str  # "A", "B", "C", "D", "F"


@dataclass
class ComparisonSample:
    prompt: str
    baseline_response: str
    finetuned_response: str
    reference: str | None = None
    winner: str = ""  # "finetuned", "baseline", "tie"


@dataclass
class ComparisonResult:
    wins: int
    losses: int
    ties: int
    improvement_pct: dict[str, float]
    samples: list[ComparisonSample | dict[str, Any]]
    latency_baseline: dict[str, float] = field(default_factory=dict)
    latency_finetuned: dict[str, float] = field(default_factory=dict)


@dataclass
class ReadinessResult:
    latency: dict[str, float]
    consistency_score: float
    edge_case_results: list[dict[str, Any]]
    format_compliance: float
    checks: dict[str, str]  # check_name -> "pass" | "warning" | "fail"
    memory_mb: float | None = None


@dataclass
class HallucinationResult:
    mode: str  # "reference", "self_consistency", "both"
    faithfulness_score: float | None
    consistency_score: float | None
    hallucination_rate: float
    flagged_samples: list[dict[str, Any]]


@dataclass
class ValidationReport:
    model_info: dict[str, Any]
    benchmark: BenchmarkResult | None
    comparison: ComparisonResult | None
    readiness: ReadinessResult | None
    hallucination: HallucinationResult | None
    overall_grade: str
    summary: str
    timestamp: str
```

```python
# adaptron/validate/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationConfig:
    model_path: str
    test_data_path: str | None = None
    baseline_model: str | None = None
    task_type: str | None = None  # auto-detect if None
    test_split_ratio: float = 0.1
    comparison_samples: int = 50
    consistency_runs: int = 3
    hallucination_temperature: float = 0.7
    hallucination_runs: int = 5
    latency_runs: int = 20
    per_sample_timeout: float = 30.0
    output_dir: str = "output/validation"
    thresholds: dict[str, Any] = field(default_factory=lambda: {
        "exact_match": {"pass": 0.8, "warning": 0.6},
        "f1": {"pass": 0.75, "warning": 0.5},
        "consistency": {"pass": 0.85, "warning": 0.7},
        "hallucination_rate": {"pass": 0.05, "warning": 0.15},
        "improvement_pct": {"pass": 20.0, "warning": 5.0},
    })
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_config.py -v`
Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/__init__.py adaptron/validate/models.py adaptron/validate/config.py tests/validate/__init__.py tests/validate/test_config.py
git commit -m "feat: validation framework data models and config"
```

---

## Phase 2: Benchmark Suite

### Task 2: Benchmark suite

**Files:**
- Create: `adaptron/validate/benchmark.py`
- Create: `tests/validate/test_benchmark.py`

**Step 1: Write failing tests**

```python
# tests/validate/test_benchmark.py
from adaptron.validate.benchmark import BenchmarkSuite
from adaptron.validate.config import ValidationConfig


def test_detect_task_type_qa():
    suite = BenchmarkSuite(ValidationConfig(model_path="/tmp/model"))
    data = [{"instruction": "What is X?", "response": "Y"}]
    assert suite.detect_task_type(data) == "qa"


def test_detect_task_type_classification():
    suite = BenchmarkSuite(ValidationConfig(model_path="/tmp/model"))
    data = [{"instruction": "Classify: good product", "response": "positive"}]
    # Short responses suggest classification
    assert suite.detect_task_type(data) == "classification"


def test_compute_qa_metrics():
    suite = BenchmarkSuite(ValidationConfig(model_path="/tmp/model"))
    predictions = ["Paris", "Berlin", "wrong"]
    references = ["Paris", "Berlin", "London"]
    metrics = suite.compute_metrics(predictions, references, task_type="qa")
    assert "exact_match" in metrics
    assert "f1" in metrics
    assert abs(metrics["exact_match"] - 2 / 3) < 0.01


def test_compute_classification_metrics():
    suite = BenchmarkSuite(ValidationConfig(model_path="/tmp/model"))
    predictions = ["positive", "negative", "positive", "negative"]
    references = ["positive", "negative", "negative", "negative"]
    metrics = suite.compute_metrics(predictions, references, task_type="classification")
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert metrics["accuracy"] == 0.75


def test_grade_metrics():
    suite = BenchmarkSuite(ValidationConfig(model_path="/tmp/model"))
    metrics = {"exact_match": 0.85, "f1": 0.90}
    grade = suite.grade_metrics(metrics)
    assert grade == "A"


def test_grade_metrics_failing():
    suite = BenchmarkSuite(ValidationConfig(model_path="/tmp/model"))
    metrics = {"exact_match": 0.3, "f1": 0.4}
    grade = suite.grade_metrics(metrics)
    assert grade in ("D", "F")
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_benchmark.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/validate/benchmark.py
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import BenchmarkResult

logger = logging.getLogger(__name__)


class BenchmarkSuite:
    """Runs task-specific metrics on finetuned model outputs."""

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config

    def detect_task_type(self, data: list[dict[str, Any]]) -> str:
        """Auto-detect task type from data shape."""
        if not data:
            return "qa"
        avg_response_len = sum(len(d.get("response", "")) for d in data) / len(data)
        # Short responses (<20 chars avg) suggest classification
        if avg_response_len < 20:
            return "classification"
        return "qa"

    def compute_metrics(
        self,
        predictions: list[str],
        references: list[str],
        task_type: str = "qa",
    ) -> dict[str, float]:
        """Compute task-specific metrics."""
        if task_type == "classification":
            return self._classification_metrics(predictions, references)
        return self._qa_metrics(predictions, references)

    def _qa_metrics(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, float]:
        """Exact match and token-level F1 for QA tasks."""
        if not predictions:
            return {"exact_match": 0.0, "f1": 0.0}

        em_count = 0
        f1_scores = []
        for pred, ref in zip(predictions, references):
            pred_norm = pred.strip().lower()
            ref_norm = ref.strip().lower()
            if pred_norm == ref_norm:
                em_count += 1
            f1_scores.append(self._token_f1(pred_norm, ref_norm))

        return {
            "exact_match": em_count / len(predictions),
            "f1": sum(f1_scores) / len(f1_scores),
        }

    def _token_f1(self, prediction: str, reference: str) -> float:
        """Token-level F1 score."""
        pred_tokens = prediction.split()
        ref_tokens = reference.split()
        if not pred_tokens or not ref_tokens:
            return 1.0 if pred_tokens == ref_tokens else 0.0

        pred_counts = Counter(pred_tokens)
        ref_counts = Counter(ref_tokens)
        common = sum((pred_counts & ref_counts).values())

        if common == 0:
            return 0.0
        precision = common / len(pred_tokens)
        recall = common / len(ref_tokens)
        return 2 * precision * recall / (precision + recall)

    def _classification_metrics(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, float]:
        """Accuracy, precision, recall, F1 for classification."""
        if not predictions:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        correct = sum(
            1 for p, r in zip(predictions, references)
            if p.strip().lower() == r.strip().lower()
        )
        accuracy = correct / len(predictions)

        # Macro-average precision/recall/f1 across all labels
        labels = set(r.strip().lower() for r in references)
        precisions, recalls = [], []
        for label in labels:
            tp = sum(1 for p, r in zip(predictions, references)
                     if p.strip().lower() == label and r.strip().lower() == label)
            fp = sum(1 for p, r in zip(predictions, references)
                     if p.strip().lower() == label and r.strip().lower() != label)
            fn = sum(1 for p, r in zip(predictions, references)
                     if p.strip().lower() != label and r.strip().lower() == label)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            precisions.append(prec)
            recalls.append(rec)

        avg_precision = sum(precisions) / len(precisions) if precisions else 0.0
        avg_recall = sum(recalls) / len(recalls) if recalls else 0.0
        f1 = (2 * avg_precision * avg_recall / (avg_precision + avg_recall)
               if (avg_precision + avg_recall) > 0 else 0.0)

        return {
            "accuracy": accuracy,
            "precision": avg_precision,
            "recall": avg_recall,
            "f1": f1,
        }

    def grade_metrics(self, metrics: dict[str, float]) -> str:
        """Assign a letter grade based on metrics and thresholds."""
        thresholds = self._config.thresholds
        grades = []
        for metric_name, value in metrics.items():
            if metric_name in thresholds:
                t = thresholds[metric_name]
                if value >= t["pass"]:
                    grades.append("A")
                elif value >= t["warning"]:
                    grades.append("C")
                else:
                    grades.append("F")

        if not grades:
            # No thresholds matched; grade by average metric value
            avg = sum(metrics.values()) / len(metrics) if metrics else 0
            if avg >= 0.8:
                return "A"
            if avg >= 0.6:
                return "B"
            if avg >= 0.4:
                return "C"
            if avg >= 0.2:
                return "D"
            return "F"

        # Worst grade wins
        order = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
        worst = min(grades, key=lambda g: order.get(g, 0))
        return worst

    def run(
        self,
        predictions: list[str],
        references: list[str],
        test_data: list[dict[str, Any]] | None = None,
    ) -> BenchmarkResult:
        """Run full benchmark and return result."""
        task_type = self._config.task_type or self.detect_task_type(test_data or [])
        metrics = self.compute_metrics(predictions, references, task_type)
        grade = self.grade_metrics(metrics)

        per_sample = []
        for i, (pred, ref) in enumerate(zip(predictions, references)):
            per_sample.append({
                "index": i,
                "expected": ref,
                "predicted": pred,
                "correct": pred.strip().lower() == ref.strip().lower(),
            })

        return BenchmarkResult(
            task_type=task_type,
            metrics=metrics,
            per_sample=per_sample,
            grade=grade,
        )
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_benchmark.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/benchmark.py tests/validate/test_benchmark.py
git commit -m "feat: benchmark suite with QA and classification metrics"
```

---

## Phase 3: Model Comparator

### Task 3: Model comparator

**Files:**
- Create: `adaptron/validate/comparator.py`
- Create: `tests/validate/test_comparator.py`

**Step 1: Write failing tests**

```python
# tests/validate/test_comparator.py
from adaptron.validate.comparator import ModelComparator
from adaptron.validate.config import ValidationConfig


def test_compute_wins_losses():
    comp = ModelComparator(ValidationConfig(model_path="/tmp/model"))
    baseline_preds = ["Paris", "wrong", "Tokyo"]
    finetuned_preds = ["Paris", "Berlin", "Tokyo"]
    references = ["Paris", "Berlin", "Tokyo"]
    wins, losses, ties = comp.compute_wins(
        baseline_preds, finetuned_preds, references
    )
    assert wins == 1  # Berlin: finetuned correct, baseline wrong
    assert losses == 0
    assert ties == 2  # Paris and Tokyo: both correct


def test_compute_improvement():
    comp = ModelComparator(ValidationConfig(model_path="/tmp/model"))
    baseline_metrics = {"exact_match": 0.60, "f1": 0.70}
    finetuned_metrics = {"exact_match": 0.80, "f1": 0.85}
    improvement = comp.compute_improvement(baseline_metrics, finetuned_metrics)
    assert abs(improvement["exact_match"] - 33.33) < 0.1
    assert abs(improvement["f1"] - 21.43) < 0.1


def test_build_samples():
    comp = ModelComparator(ValidationConfig(model_path="/tmp/model"))
    prompts = ["What is 1+1?"]
    baseline_preds = ["3"]
    finetuned_preds = ["2"]
    references = ["2"]
    samples = comp.build_samples(prompts, baseline_preds, finetuned_preds, references)
    assert len(samples) == 1
    assert samples[0].winner == "finetuned"
    assert samples[0].finetuned_response == "2"
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_comparator.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/validate/comparator.py
from __future__ import annotations

import logging
from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import ComparisonResult, ComparisonSample

logger = logging.getLogger(__name__)


class ModelComparator:
    """Compares finetuned model against a baseline on the same prompts."""

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config

    def compute_wins(
        self,
        baseline_preds: list[str],
        finetuned_preds: list[str],
        references: list[str],
    ) -> tuple[int, int, int]:
        """Count wins/losses/ties for finetuned vs baseline."""
        wins, losses, ties = 0, 0, 0
        for bp, fp, ref in zip(baseline_preds, finetuned_preds, references):
            ref_norm = ref.strip().lower()
            b_correct = bp.strip().lower() == ref_norm
            f_correct = fp.strip().lower() == ref_norm
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
        """Compute percentage improvement per metric."""
        improvement = {}
        for key in finetuned_metrics:
            if key in baseline_metrics and baseline_metrics[key] > 0:
                pct = ((finetuned_metrics[key] - baseline_metrics[key])
                       / baseline_metrics[key] * 100)
                improvement[key] = round(pct, 2)
            else:
                improvement[key] = 0.0
        return improvement

    def build_samples(
        self,
        prompts: list[str],
        baseline_preds: list[str],
        finetuned_preds: list[str],
        references: list[str] | None = None,
    ) -> list[ComparisonSample]:
        """Build side-by-side comparison samples."""
        refs = references or [""] * len(prompts)
        samples = []
        for prompt, bp, fp, ref in zip(prompts, baseline_preds, finetuned_preds, refs):
            ref_norm = ref.strip().lower() if ref else None
            if ref_norm:
                b_correct = bp.strip().lower() == ref_norm
                f_correct = fp.strip().lower() == ref_norm
                if f_correct and not b_correct:
                    winner = "finetuned"
                elif b_correct and not f_correct:
                    winner = "baseline"
                else:
                    winner = "tie"
            else:
                winner = ""
            samples.append(ComparisonSample(
                prompt=prompt,
                baseline_response=bp,
                finetuned_response=fp,
                reference=ref or None,
                winner=winner,
            ))
        return samples

    def run(
        self,
        prompts: list[str],
        baseline_preds: list[str],
        finetuned_preds: list[str],
        references: list[str],
        baseline_metrics: dict[str, float],
        finetuned_metrics: dict[str, float],
    ) -> ComparisonResult:
        """Run full comparison and return result."""
        wins, losses, ties = self.compute_wins(
            baseline_preds, finetuned_preds, references
        )
        improvement = self.compute_improvement(baseline_metrics, finetuned_metrics)
        samples = self.build_samples(
            prompts, baseline_preds, finetuned_preds, references
        )
        return ComparisonResult(
            wins=wins,
            losses=losses,
            ties=ties,
            improvement_pct=improvement,
            samples=samples,
        )
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_comparator.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/comparator.py tests/validate/test_comparator.py
git commit -m "feat: model comparator for base vs finetuned comparison"
```

---

## Phase 4: Production Readiness

### Task 4: Production readiness checks

**Files:**
- Create: `adaptron/validate/readiness.py`
- Create: `tests/validate/test_readiness.py`

**Step 1: Write failing tests**

```python
# tests/validate/test_readiness.py
from adaptron.validate.readiness import ProductionReadiness
from adaptron.validate.config import ValidationConfig


def test_compute_latency_stats():
    pr = ProductionReadiness(ValidationConfig(model_path="/tmp/model"))
    durations_ms = [100, 110, 105, 200, 300, 95, 102, 108, 115, 500]
    stats = pr.compute_latency_stats(durations_ms)
    assert "p50_ms" in stats
    assert "p95_ms" in stats
    assert "p99_ms" in stats
    assert stats["p50_ms"] <= stats["p95_ms"] <= stats["p99_ms"]


def test_check_consistency_high():
    pr = ProductionReadiness(ValidationConfig(model_path="/tmp/model"))
    # All responses identical = perfect consistency
    responses_per_prompt = [
        ["The answer is 42", "The answer is 42", "The answer is 42"],
    ]
    score = pr.check_consistency(responses_per_prompt)
    assert score == 1.0


def test_check_consistency_low():
    pr = ProductionReadiness(ValidationConfig(model_path="/tmp/model"))
    # All responses completely different
    responses_per_prompt = [
        ["yes", "no", "maybe"],
    ]
    score = pr.check_consistency(responses_per_prompt)
    assert score < 1.0


def test_check_format_compliance():
    pr = ProductionReadiness(ValidationConfig(model_path="/tmp/model"))
    expected_formats = ["json", "list", "text"]
    actual_outputs = ['{"key": "value"}', "1. item\n2. item", "some text"]
    compliance = pr.check_format_compliance(expected_formats, actual_outputs)
    assert compliance == 1.0


def test_check_format_compliance_partial():
    pr = ProductionReadiness(ValidationConfig(model_path="/tmp/model"))
    expected_formats = ["json", "json"]
    actual_outputs = ['{"key": "value"}', "not json at all"]
    compliance = pr.check_format_compliance(expected_formats, actual_outputs)
    assert compliance == 0.5
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_readiness.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/validate/readiness.py
from __future__ import annotations

import json
import logging
import statistics
from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import ReadinessResult

logger = logging.getLogger(__name__)


class ProductionReadiness:
    """Runs non-functional production readiness checks."""

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config

    def compute_latency_stats(self, durations_ms: list[float]) -> dict[str, float]:
        """Compute p50, p95, p99 latency stats from a list of durations in ms."""
        if not durations_ms:
            return {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "mean_ms": 0}
        sorted_d = sorted(durations_ms)
        n = len(sorted_d)
        return {
            "p50_ms": sorted_d[int(n * 0.50)],
            "p95_ms": sorted_d[min(int(n * 0.95), n - 1)],
            "p99_ms": sorted_d[min(int(n * 0.99), n - 1)],
            "mean_ms": statistics.mean(sorted_d),
        }

    def check_consistency(
        self, responses_per_prompt: list[list[str]]
    ) -> float:
        """Check response consistency across multiple runs of the same prompt.

        Returns a score 0-1 where 1.0 = all responses identical.
        """
        if not responses_per_prompt:
            return 1.0

        scores = []
        for responses in responses_per_prompt:
            if len(responses) <= 1:
                scores.append(1.0)
                continue
            # Pairwise exact match ratio
            pairs = 0
            matches = 0
            for i in range(len(responses)):
                for j in range(i + 1, len(responses)):
                    pairs += 1
                    if responses[i].strip().lower() == responses[j].strip().lower():
                        matches += 1
            scores.append(matches / pairs if pairs > 0 else 1.0)

        return sum(scores) / len(scores)

    def check_format_compliance(
        self, expected_formats: list[str], actual_outputs: list[str]
    ) -> float:
        """Check if outputs match expected formats. Returns compliance ratio 0-1."""
        if not expected_formats:
            return 1.0

        compliant = 0
        for fmt, output in zip(expected_formats, actual_outputs):
            if self._matches_format(fmt, output):
                compliant += 1
        return compliant / len(expected_formats)

    def _matches_format(self, expected: str, output: str) -> bool:
        """Check if output matches the expected format."""
        output = output.strip()
        if expected == "json":
            try:
                json.loads(output)
                return True
            except (json.JSONDecodeError, ValueError):
                return False
        if expected == "list":
            lines = output.split("\n")
            return any(
                line.strip().startswith(("- ", "* ", "1.", "1)"))
                for line in lines
            )
        # "text" or unknown format always passes
        return True

    def run(
        self,
        latency_durations_ms: list[float],
        responses_per_prompt: list[list[str]],
        edge_case_results: list[dict[str, Any]] | None = None,
        format_checks: tuple[list[str], list[str]] | None = None,
    ) -> ReadinessResult:
        """Run all production readiness checks."""
        latency = self.compute_latency_stats(latency_durations_ms)
        consistency = self.check_consistency(responses_per_prompt)

        format_compliance = 1.0
        if format_checks:
            format_compliance = self.check_format_compliance(*format_checks)

        # Determine check statuses
        thresholds = self._config.thresholds
        consistency_t = thresholds.get("consistency", {"pass": 0.85, "warning": 0.7})

        checks: dict[str, str] = {}
        if consistency >= consistency_t["pass"]:
            checks["consistency"] = "pass"
        elif consistency >= consistency_t["warning"]:
            checks["consistency"] = "warning"
        else:
            checks["consistency"] = "fail"

        checks["format_compliance"] = "pass" if format_compliance >= 0.9 else "warning"
        checks["latency"] = "pass"  # Advisory only

        return ReadinessResult(
            latency=latency,
            consistency_score=consistency,
            edge_case_results=edge_case_results or [],
            format_compliance=format_compliance,
            checks=checks,
        )
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_readiness.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/readiness.py tests/validate/test_readiness.py
git commit -m "feat: production readiness checks (latency, consistency, format)"
```

---

## Phase 5: Hallucination Detector

### Task 5: Hallucination detector

**Files:**
- Create: `adaptron/validate/hallucination.py`
- Create: `tests/validate/test_hallucination.py`

**Step 1: Write failing tests**

```python
# tests/validate/test_hallucination.py
from adaptron.validate.hallucination import HallucinationDetector
from adaptron.validate.config import ValidationConfig


def test_reference_faithfulness_perfect():
    hd = HallucinationDetector(ValidationConfig(model_path="/tmp/model"))
    predictions = ["Paris is the capital of France"]
    references = ["Paris is the capital of France"]
    score = hd.compute_faithfulness(predictions, references)
    assert score == 1.0


def test_reference_faithfulness_partial():
    hd = HallucinationDetector(ValidationConfig(model_path="/tmp/model"))
    predictions = ["Paris is the capital of Germany"]
    references = ["Paris is the capital of France"]
    score = hd.compute_faithfulness(predictions, references)
    assert 0.0 < score < 1.0


def test_self_consistency_identical():
    hd = HallucinationDetector(ValidationConfig(model_path="/tmp/model"))
    runs = [
        ["The answer is 42", "The answer is 42", "The answer is 42"],
    ]
    score = hd.compute_self_consistency(runs)
    assert score == 1.0


def test_self_consistency_divergent():
    hd = HallucinationDetector(ValidationConfig(model_path="/tmp/model"))
    runs = [
        ["yes", "no", "maybe"],
    ]
    score = hd.compute_self_consistency(runs)
    assert score < 1.0


def test_hallucination_rate():
    hd = HallucinationDetector(ValidationConfig(model_path="/tmp/model"))
    predictions = ["correct answer", "hallucinated nonsense", "correct again"]
    references = ["correct answer", "actual answer", "correct again"]
    rate, flagged = hd.compute_hallucination_rate(predictions, references)
    assert 0.0 < rate < 1.0
    assert len(flagged) == 1
    assert flagged[0]["index"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_hallucination.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/validate/hallucination.py
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import HallucinationResult

logger = logging.getLogger(__name__)


class HallucinationDetector:
    """Detects hallucinations via reference comparison or self-consistency."""

    def __init__(self, config: ValidationConfig) -> None:
        self._config = config

    def _token_overlap(self, text_a: str, text_b: str) -> float:
        """Compute token overlap ratio between two texts."""
        tokens_a = set(text_a.strip().lower().split())
        tokens_b = set(text_b.strip().lower().split())
        if not tokens_a or not tokens_b:
            return 1.0 if tokens_a == tokens_b else 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union) if union else 0.0

    def compute_faithfulness(
        self, predictions: list[str], references: list[str]
    ) -> float:
        """Compute faithfulness score (0-1) based on token overlap with references."""
        if not predictions:
            return 1.0
        scores = [
            self._token_overlap(pred, ref)
            for pred, ref in zip(predictions, references)
        ]
        return sum(scores) / len(scores)

    def compute_self_consistency(
        self, responses_per_prompt: list[list[str]]
    ) -> float:
        """Compute consistency score from multiple runs per prompt."""
        if not responses_per_prompt:
            return 1.0

        prompt_scores = []
        for responses in responses_per_prompt:
            if len(responses) <= 1:
                prompt_scores.append(1.0)
                continue
            pair_scores = []
            for i in range(len(responses)):
                for j in range(i + 1, len(responses)):
                    pair_scores.append(
                        self._token_overlap(responses[i], responses[j])
                    )
            prompt_scores.append(
                sum(pair_scores) / len(pair_scores) if pair_scores else 1.0
            )
        return sum(prompt_scores) / len(prompt_scores)

    def compute_hallucination_rate(
        self, predictions: list[str], references: list[str],
        threshold: float = 0.5,
    ) -> tuple[float, list[dict[str, Any]]]:
        """Compute hallucination rate and return flagged samples.

        A sample is flagged as hallucinated if its token overlap with the
        reference falls below the threshold.
        """
        if not predictions:
            return 0.0, []

        flagged = []
        for i, (pred, ref) in enumerate(zip(predictions, references)):
            overlap = self._token_overlap(pred, ref)
            if overlap < threshold:
                flagged.append({
                    "index": i,
                    "prediction": pred,
                    "reference": ref,
                    "overlap_score": round(overlap, 4),
                })

        rate = len(flagged) / len(predictions)
        return rate, flagged

    def run(
        self,
        predictions: list[str] | None = None,
        references: list[str] | None = None,
        responses_per_prompt: list[list[str]] | None = None,
    ) -> HallucinationResult:
        """Run hallucination detection. Uses reference-based when references
        exist, self-consistency when multiple runs exist, or both."""
        faithfulness = None
        consistency = None
        hallucination_rate = 0.0
        flagged: list[dict[str, Any]] = []

        has_references = predictions is not None and references is not None
        has_multi_runs = responses_per_prompt is not None

        if has_references and has_multi_runs:
            mode = "both"
        elif has_references:
            mode = "reference"
        elif has_multi_runs:
            mode = "self_consistency"
        else:
            mode = "reference"
            return HallucinationResult(
                mode=mode, faithfulness_score=1.0,
                consistency_score=None, hallucination_rate=0.0,
                flagged_samples=[],
            )

        if has_references:
            faithfulness = self.compute_faithfulness(predictions, references)
            hallucination_rate, flagged = self.compute_hallucination_rate(
                predictions, references
            )

        if has_multi_runs:
            consistency = self.compute_self_consistency(responses_per_prompt)

        return HallucinationResult(
            mode=mode,
            faithfulness_score=faithfulness,
            consistency_score=consistency,
            hallucination_rate=hallucination_rate,
            flagged_samples=flagged,
        )
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_hallucination.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/hallucination.py tests/validate/test_hallucination.py
git commit -m "feat: hallucination detector with reference and self-consistency modes"
```

---

## Phase 6: Report Generator

### Task 6: Report generator (JSON + HTML)

**Files:**
- Create: `adaptron/validate/report.py`
- Create: `adaptron/validate/templates/report.html`
- Create: `tests/validate/test_report.py`

**Step 1: Write failing tests**

```python
# tests/validate/test_report.py
import json
from pathlib import Path
from adaptron.validate.report import ReportGenerator
from adaptron.validate.models import (
    BenchmarkResult,
    ReadinessResult,
    HallucinationResult,
    ValidationReport,
)


def _make_report() -> ValidationReport:
    return ValidationReport(
        model_info={"name": "test-model", "base_model": "base", "training_mode": "qlora"},
        benchmark=BenchmarkResult(
            task_type="qa",
            metrics={"exact_match": 0.85, "f1": 0.90},
            per_sample=[{"index": 0, "correct": True}],
            grade="A",
        ),
        comparison=None,
        readiness=ReadinessResult(
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 150},
            consistency_score=0.92,
            edge_case_results=[],
            format_compliance=1.0,
            checks={"latency": "pass", "consistency": "pass"},
        ),
        hallucination=HallucinationResult(
            mode="reference",
            faithfulness_score=0.95,
            consistency_score=None,
            hallucination_rate=0.05,
            flagged_samples=[],
        ),
        overall_grade="A",
        summary="Model passes all validation checks.",
        timestamp="2026-03-08T00:00:00",
    )


def test_generate_json(tmp_path):
    gen = ReportGenerator(output_dir=str(tmp_path))
    report = _make_report()
    json_path = gen.generate_json(report)
    assert Path(json_path).exists()
    data = json.loads(Path(json_path).read_text())
    assert data["overall_grade"] == "A"
    assert data["benchmark"]["metrics"]["exact_match"] == 0.85


def test_generate_html(tmp_path):
    gen = ReportGenerator(output_dir=str(tmp_path))
    report = _make_report()
    html_path = gen.generate_html(report)
    assert Path(html_path).exists()
    content = Path(html_path).read_text()
    assert "test-model" in content
    assert "Grade: A" in content


def test_generate_both(tmp_path):
    gen = ReportGenerator(output_dir=str(tmp_path))
    report = _make_report()
    json_path, html_path = gen.generate(report)
    assert Path(json_path).exists()
    assert Path(html_path).exists()
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_report.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/validate/report.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adaptron.validate.models import ValidationReport

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Adaptron Model Validation Report</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; }
  h1 { border-bottom: 2px solid #2563eb; padding-bottom: 10px; }
  .grade { font-size: 48px; font-weight: bold; text-align: center; padding: 20px;
           border-radius: 12px; margin: 20px 0; }
  .grade-A { background: #dcfce7; color: #166534; }
  .grade-B { background: #dbeafe; color: #1e40af; }
  .grade-C { background: #fef9c3; color: #854d0e; }
  .grade-D { background: #fed7aa; color: #9a3412; }
  .grade-F { background: #fecaca; color: #991b1b; }
  .section { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
             padding: 20px; margin: 20px 0; }
  .section h2 { margin-top: 0; color: #1e293b; }
  table { width: 100%; border-collapse: collapse; margin: 10px 0; }
  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
  th { background: #f1f5f9; font-weight: 600; }
  .pass { color: #166534; } .warning { color: #854d0e; } .fail { color: #991b1b; }
  .summary { font-size: 16px; line-height: 1.6; padding: 15px; background: #eff6ff;
             border-radius: 8px; margin: 15px 0; }
  .meta { color: #64748b; font-size: 14px; }
</style>
</head>
<body>
<h1>Adaptron Model Validation Report</h1>
<p class="meta">Model: {{ model_name }} | Base: {{ base_model }} | Generated: {{ timestamp }}</p>

<div class="grade grade-{{ overall_grade }}">Grade: {{ overall_grade }}</div>
<div class="summary">{{ summary }}</div>

{% if benchmark %}
<div class="section">
<h2>Benchmark Results ({{ benchmark.task_type }})</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{% for key, val in benchmark.metrics.items() %}
<tr><td>{{ key }}</td><td>{{ "%.4f"|format(val) }}</td></tr>
{% endfor %}
</table>
<p>Grade: <strong>{{ benchmark.grade }}</strong> | Samples: {{ benchmark.per_sample|length }}</p>
</div>
{% endif %}

{% if comparison %}
<div class="section">
<h2>Model Comparison</h2>
<table>
<tr><th>Wins</th><th>Losses</th><th>Ties</th></tr>
<tr><td>{{ comparison.wins }}</td><td>{{ comparison.losses }}</td><td>{{ comparison.ties }}</td></tr>
</table>
{% if comparison.improvement_pct %}
<h3>Improvement</h3>
<table>
<tr><th>Metric</th><th>Change %</th></tr>
{% for key, val in comparison.improvement_pct.items() %}
<tr><td>{{ key }}</td><td>{{ "%.2f"|format(val) }}%</td></tr>
{% endfor %}
</table>
{% endif %}
</div>
{% endif %}

{% if readiness %}
<div class="section">
<h2>Production Readiness</h2>
<table>
<tr><th>Check</th><th>Status</th></tr>
{% for check, status in readiness.checks.items() %}
<tr><td>{{ check }}</td><td class="{{ status }}">{{ status }}</td></tr>
{% endfor %}
</table>
<h3>Latency</h3>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{% for key, val in readiness.latency.items() %}
<tr><td>{{ key }}</td><td>{{ "%.1f"|format(val) }} ms</td></tr>
{% endfor %}
</table>
<p>Consistency: {{ "%.2f"|format(readiness.consistency_score) }} | Format Compliance: {{ "%.2f"|format(readiness.format_compliance) }}</p>
</div>
{% endif %}

{% if hallucination %}
<div class="section">
<h2>Hallucination Detection ({{ hallucination.mode }})</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Hallucination Rate</td><td>{{ "%.2f"|format(hallucination.hallucination_rate * 100) }}%</td></tr>
{% if hallucination.faithfulness_score is not none %}
<tr><td>Faithfulness Score</td><td>{{ "%.4f"|format(hallucination.faithfulness_score) }}</td></tr>
{% endif %}
{% if hallucination.consistency_score is not none %}
<tr><td>Consistency Score</td><td>{{ "%.4f"|format(hallucination.consistency_score) }}</td></tr>
{% endif %}
</table>
<p>Flagged samples: {{ hallucination.flagged_samples|length }}</p>
</div>
{% endif %}

<p class="meta">Generated by Adaptron Model Validation Framework</p>
</body>
</html>"""


class ReportGenerator:
    """Generates HTML and JSON validation reports."""

    def __init__(self, output_dir: str = "output/validation") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _report_to_dict(self, report: ValidationReport) -> dict[str, Any]:
        """Convert report to a JSON-serializable dict."""
        return asdict(report)

    def generate_json(self, report: ValidationReport) -> str:
        """Generate JSON report file. Returns the file path."""
        data = self._report_to_dict(report)
        path = self._output_dir / "report.json"
        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)

    def generate_html(self, report: ValidationReport) -> str:
        """Generate HTML report file. Returns the file path."""
        try:
            from jinja2 import Template
            template = Template(HTML_TEMPLATE)
        except ImportError:
            # Fallback: simple string replacement if jinja2 not available
            return self._generate_html_fallback(report)

        model_info = report.model_info or {}
        html = template.render(
            model_name=model_info.get("name", "unknown"),
            base_model=model_info.get("base_model", "unknown"),
            timestamp=report.timestamp,
            overall_grade=report.overall_grade,
            summary=report.summary,
            benchmark=report.benchmark,
            comparison=report.comparison,
            readiness=report.readiness,
            hallucination=report.hallucination,
        )
        path = self._output_dir / "report.html"
        path.write_text(html)
        return str(path)

    def _generate_html_fallback(self, report: ValidationReport) -> str:
        """Simple HTML fallback without Jinja2."""
        model_info = report.model_info or {}
        html = f"""<!DOCTYPE html>
<html><head><title>Validation Report</title></head><body>
<h1>Adaptron Model Validation Report</h1>
<p>Model: {model_info.get('name', 'unknown')}</p>
<h2>Grade: {report.overall_grade}</h2>
<p>{report.summary}</p>
<p>Generated: {report.timestamp}</p>
</body></html>"""
        path = self._output_dir / "report.html"
        path.write_text(html)
        return str(path)

    def generate(self, report: ValidationReport) -> tuple[str, str]:
        """Generate both JSON and HTML reports. Returns (json_path, html_path)."""
        json_path = self.generate_json(report)
        html_path = self.generate_html(report)
        return json_path, html_path
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_report.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/report.py tests/validate/test_report.py
git commit -m "feat: report generator with HTML and JSON output"
```

---

## Phase 7: Validation Engine

### Task 7: Validation engine orchestrator

**Files:**
- Create: `adaptron/validate/engine.py`
- Create: `tests/validate/test_engine.py`

**Step 1: Write failing tests**

```python
# tests/validate/test_engine.py
from adaptron.validate.engine import ValidationEngine
from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import ValidationReport


def test_engine_compute_overall_grade_all_pass():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    grade = engine.compute_overall_grade(
        benchmark_grade="A",
        hallucination_rate=0.03,
        improvement_pct=25.0,
    )
    assert grade == "A"


def test_engine_compute_overall_grade_some_warnings():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    grade = engine.compute_overall_grade(
        benchmark_grade="C",
        hallucination_rate=0.08,
        improvement_pct=10.0,
    )
    assert grade == "C"


def test_engine_compute_overall_grade_failing():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    grade = engine.compute_overall_grade(
        benchmark_grade="F",
        hallucination_rate=0.35,
        improvement_pct=-5.0,
    )
    assert grade == "F"


def test_engine_generate_summary():
    engine = ValidationEngine(ValidationConfig(model_path="/tmp/model"))
    summary = engine.generate_summary(
        overall_grade="B",
        benchmark_grade="B",
        hallucination_rate=0.08,
        improvement_pct=15.0,
    )
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "B" in summary
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/validate/test_engine.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/validate/engine.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.validate.benchmark import BenchmarkSuite
from adaptron.validate.comparator import ModelComparator
from adaptron.validate.config import ValidationConfig
from adaptron.validate.hallucination import HallucinationDetector
from adaptron.validate.models import (
    ComparisonResult,
    HallucinationResult,
    ValidationReport,
)
from adaptron.validate.readiness import ProductionReadiness
from adaptron.validate.report import ReportGenerator

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Orchestrates all validators and produces the final report."""

    def __init__(
        self,
        config: ValidationConfig,
        event_bus: EventBus | None = None,
    ) -> None:
        self._config = config
        self._bus = event_bus or EventBus()
        self._benchmark = BenchmarkSuite(config)
        self._comparator = ModelComparator(config)
        self._readiness = ProductionReadiness(config)
        self._hallucination = HallucinationDetector(config)
        self._reporter = ReportGenerator(output_dir=config.output_dir)

    def _emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        self._bus.emit(event_type, Event(type=event_type, data=data or {}))

    def compute_overall_grade(
        self,
        benchmark_grade: str,
        hallucination_rate: float,
        improvement_pct: float | None = None,
    ) -> str:
        """Compute overall A-F grade from component results."""
        grade_order = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        benchmark_score = grade_order.get(benchmark_grade, 0)

        # Hallucination grade
        h_thresholds = self._config.thresholds.get(
            "hallucination_rate", {"pass": 0.05, "warning": 0.15}
        )
        if hallucination_rate < h_thresholds["pass"]:
            halluc_score = 4
        elif hallucination_rate < h_thresholds["warning"]:
            halluc_score = 2
        else:
            halluc_score = 0

        # Improvement grade (optional)
        imp_score = 3  # default B if no comparison
        if improvement_pct is not None:
            imp_thresholds = self._config.thresholds.get(
                "improvement_pct", {"pass": 20.0, "warning": 5.0}
            )
            if improvement_pct >= imp_thresholds["pass"]:
                imp_score = 4
            elif improvement_pct >= imp_thresholds["warning"]:
                imp_score = 2
            else:
                imp_score = 0

        avg_score = (benchmark_score + halluc_score + imp_score) / 3
        if avg_score >= 3.5:
            return "A"
        if avg_score >= 2.5:
            return "B"
        if avg_score >= 1.5:
            return "C"
        if avg_score >= 0.5:
            return "D"
        return "F"

    def generate_summary(
        self,
        overall_grade: str,
        benchmark_grade: str,
        hallucination_rate: float,
        improvement_pct: float | None = None,
    ) -> str:
        """Generate a human-readable summary paragraph."""
        parts = [f"Overall grade: {overall_grade}."]
        parts.append(f"Benchmark grade: {benchmark_grade}.")

        if hallucination_rate < 0.05:
            parts.append("Hallucination rate is low (<5%).")
        elif hallucination_rate < 0.15:
            parts.append(f"Hallucination rate is moderate ({hallucination_rate:.0%}).")
        else:
            parts.append(f"Hallucination rate is high ({hallucination_rate:.0%}) — review flagged samples.")

        if improvement_pct is not None:
            if improvement_pct > 0:
                parts.append(f"Model shows {improvement_pct:.1f}% improvement over baseline.")
            else:
                parts.append(f"Model shows {abs(improvement_pct):.1f}% regression vs baseline.")

        return " ".join(parts)

    def validate(
        self,
        predictions: list[str],
        references: list[str],
        test_data: list[dict[str, Any]] | None = None,
        prompts: list[str] | None = None,
        baseline_preds: list[str] | None = None,
        latency_durations_ms: list[float] | None = None,
        responses_per_prompt: list[list[str]] | None = None,
        model_info: dict[str, Any] | None = None,
    ) -> ValidationReport:
        """Run all validators and produce a report."""
        self._emit("validation_start", {"model": self._config.model_path})

        # 1. Benchmark
        benchmark_result = self._benchmark.run(predictions, references, test_data)

        # 2. Comparison (optional)
        comparison_result = None
        improvement_pct = None
        if baseline_preds is not None and prompts is not None:
            baseline_metrics = self._benchmark.compute_metrics(
                baseline_preds, references,
                self._config.task_type or self._benchmark.detect_task_type(test_data or []),
            )
            comparison_result = self._comparator.run(
                prompts, baseline_preds, predictions, references,
                baseline_metrics, benchmark_result.metrics,
            )
            # Average improvement
            if comparison_result.improvement_pct:
                improvement_pct = sum(comparison_result.improvement_pct.values()) / len(
                    comparison_result.improvement_pct
                )

        # 3. Readiness (optional)
        readiness_result = None
        if latency_durations_ms is not None or responses_per_prompt is not None:
            readiness_result = self._readiness.run(
                latency_durations_ms=latency_durations_ms or [],
                responses_per_prompt=responses_per_prompt or [],
            )

        # 4. Hallucination
        hallucination_result = self._hallucination.run(
            predictions=predictions,
            references=references,
            responses_per_prompt=responses_per_prompt,
        )

        # Grade & summary
        overall_grade = self.compute_overall_grade(
            benchmark_grade=benchmark_result.grade,
            hallucination_rate=hallucination_result.hallucination_rate,
            improvement_pct=improvement_pct,
        )
        summary = self.generate_summary(
            overall_grade=overall_grade,
            benchmark_grade=benchmark_result.grade,
            hallucination_rate=hallucination_result.hallucination_rate,
            improvement_pct=improvement_pct,
        )

        report = ValidationReport(
            model_info=model_info or {"name": "unknown"},
            benchmark=benchmark_result,
            comparison=comparison_result,
            readiness=readiness_result,
            hallucination=hallucination_result,
            overall_grade=overall_grade,
            summary=summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Generate reports
        self._reporter.generate(report)

        self._emit("validation_complete", {"grade": overall_grade})
        self._emit("validation_grade", {"grade": overall_grade, "summary": summary})

        return report
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/validate/test_engine.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add adaptron/validate/engine.py tests/validate/test_engine.py
git commit -m "feat: validation engine orchestrating all validators"
```

---

## Phase 8: CLI & API Integration

### Task 8: CLI validate command

**Files:**
- Modify: `adaptron/cli/main.py`
- Create: `tests/cli/test_validate.py`

**Step 1: Write failing tests**

```python
# tests/cli/test_validate.py
from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()


def test_validate_command_exists():
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "validate" in result.output.lower() or "model" in result.output.lower()


def test_validate_missing_model(tmp_path):
    result = runner.invoke(app, ["validate", "--model", str(tmp_path / "nonexistent")])
    assert result.exit_code != 0
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/cli/test_validate.py -v`
Expected: FAIL

**Step 3: Add validate command to CLI**

Add to `adaptron/cli/main.py` after the `research` command (before `if __name__`):

```python
@app.command()
def validate(
    model: Path = typer.Option(..., help="Path to finetuned model"),
    test_data: Path = typer.Option(None, help="Path to test data JSONL"),
    baseline: str = typer.Option(None, help="Baseline model name for comparison"),
    output_dir: Path = typer.Option("output/validation", help="Output directory for reports"),
):
    """Validate a finetuned model for production readiness."""
    if not model.exists():
        console.print(f"[red]Model path not found: {model}[/red]")
        raise typer.Exit(code=1)

    from adaptron.validate.config import ValidationConfig
    from adaptron.validate.engine import ValidationEngine

    config = ValidationConfig(
        model_path=str(model),
        test_data_path=str(test_data) if test_data else None,
        baseline_model=baseline,
        output_dir=str(output_dir),
    )

    console.print("[blue]Starting model validation...[/blue]")
    console.print(f"  Model: {model}")
    if test_data:
        console.print(f"  Test data: {test_data}")
    if baseline:
        console.print(f"  Baseline: {baseline}")

    console.print("[yellow]Full validation requires model inference. Reports will be generated at:[/yellow]")
    console.print(f"  HTML: {output_dir}/report.html")
    console.print(f"  JSON: {output_dir}/report.json")
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/cli/test_validate.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add adaptron/cli/main.py tests/cli/test_validate.py
git commit -m "feat: CLI validate command for model validation"
```

---

### Task 9: API validate routes

**Files:**
- Create: `adaptron/api/routes/validate.py`
- Modify: `adaptron/api/main.py`
- Create: `tests/api/test_validate.py`

**Step 1: Write failing tests**

```python
# tests/api/test_validate.py
import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_validate_status(client):
    response = client.get("/api/validate/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data


def test_validate_report_empty(client):
    response = client.get("/api/validate/report")
    assert response.status_code == 200
    data = response.json()
    assert "report" in data
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/api/test_validate.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/api/routes/validate.py
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/validate", tags=["validate"])

_active_report = None


@router.get("/status")
def validate_status():
    if _active_report is None:
        return {"running": False, "message": "No validation in progress"}
    return {"running": False, "grade": _active_report.overall_grade}


@router.get("/report")
def validate_report():
    if _active_report is None:
        return {"report": None}
    from dataclasses import asdict
    return {"report": asdict(_active_report)}


@router.post("/start")
async def validate_start(body: dict | None = None):
    return {"status": "accepted", "message": "Validation requires model path. Use CLI for full validation."}
```

Add to `adaptron/api/main.py` after the research router:

```python
from adaptron.api.routes.validate import router as validate_router
app.include_router(validate_router)
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/api/test_validate.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add adaptron/api/routes/validate.py adaptron/api/main.py tests/api/test_validate.py
git commit -m "feat: API validate routes for status and report retrieval"
```

---

## Phase 9: Pipeline Integration

### Task 10: ValidateStage in pipeline factory

**Files:**
- Modify: `adaptron/core/factory.py`
- Modify: `tests/integration/test_pipeline_e2e.py`

**Step 1: Write failing tests**

Update `tests/integration/test_pipeline_e2e.py` — add a test that checks the pipeline has a validate stage:

```python
def test_pipeline_has_validate_stage():
    from adaptron.core.config import PipelineConfig
    from adaptron.core.factory import PipelineFactory

    config = PipelineConfig.from_defaults()
    pipeline = PipelineFactory.create(config)
    stage_names = [name for name, _ in pipeline._stages]
    assert "validate" in stage_names
```

**Step 2: Run test to verify it fails**

Run: `py -m pytest tests/integration/test_pipeline_e2e.py::test_pipeline_has_validate_stage -v`
Expected: FAIL

**Step 3: Add ValidateStage to factory**

Add to `adaptron/core/factory.py` after the `SynthesizeStage` class:

```python
class ValidateStage:
    """Validate stage — placeholder for post-training model validation."""
    name = "validate"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        # Validation runs after training; in the pipeline it's a placeholder
        # that records that validation should be performed.
        context["validation_pending"] = True
        return StageResult(
            status=StageStatus.COMPLETED,
            output={"validation_pending": True, "message": "Run 'adaptron validate' after training"},
        )
```

Add to `PipelineFactory.create()` after the synthesize stage:

```python
pipeline.add_stage("validate", ValidateStage(config))
```

**Step 4: Update existing pipeline tests**

The existing `test_pipeline_e2e.py` test checks `len(pipeline._stages) == 4` — update to 5. Also update any stage count or event count assertions.

**Step 5: Run all tests to verify they pass**

Run: `py -m pytest tests/integration/test_pipeline_e2e.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add adaptron/core/factory.py tests/integration/test_pipeline_e2e.py
git commit -m "feat: add ValidateStage to pipeline factory"
```

---

## Phase 10: E2E Integration Test

### Task 11: End-to-end validation integration test

**Files:**
- Create: `tests/integration/test_validate_e2e.py`

**Step 1: Write the test**

```python
# tests/integration/test_validate_e2e.py
from adaptron.validate.config import ValidationConfig
from adaptron.validate.engine import ValidationEngine
from adaptron.core.events import EventBus, Event


def test_full_validation_pipeline(tmp_path):
    """E2E: run all validators, generate reports, check grade."""
    config = ValidationConfig(
        model_path=str(tmp_path / "model"),
        output_dir=str(tmp_path / "reports"),
    )

    bus = EventBus()
    events: list[Event] = []
    bus.on("*", lambda e: events.append(e))

    engine = ValidationEngine(config=config, event_bus=bus)

    # Simulate model predictions vs references
    predictions = ["Paris", "Berlin", "Tokyo", "London", "Rome"]
    references = ["Paris", "Berlin", "Tokyo", "Madrid", "Rome"]
    prompts = [f"Question {i}" for i in range(5)]

    report = engine.validate(
        predictions=predictions,
        references=references,
        prompts=prompts,
        baseline_preds=["Paris", "wrong", "Tokyo", "wrong", "wrong"],
        latency_durations_ms=[100, 110, 95, 105, 200, 150, 130, 120, 115, 180,
                              100, 110, 95, 105, 200, 150, 130, 120, 115, 180],
        responses_per_prompt=[
            ["Paris", "Paris", "Paris"],
            ["Berlin", "Berlin", "Berlin"],
            ["Tokyo", "Tokyo", "Tokyo"],
        ],
        model_info={"name": "test-model", "base_model": "base", "training_mode": "qlora"},
    )

    # Check report structure
    assert report.overall_grade in ("A", "B", "C", "D", "F")
    assert report.benchmark is not None
    assert report.benchmark.metrics["exact_match"] == 0.8
    assert report.comparison is not None
    assert report.comparison.wins > 0
    assert report.readiness is not None
    assert report.hallucination is not None
    assert len(report.summary) > 0

    # Check reports generated
    from pathlib import Path
    assert (Path(tmp_path / "reports" / "report.json")).exists()
    assert (Path(tmp_path / "reports" / "report.html")).exists()

    # Check events
    event_types = [e.type for e in events]
    assert "validation_start" in event_types
    assert "validation_complete" in event_types
    assert "validation_grade" in event_types
```

**Step 2: Run test**

Run: `py -m pytest tests/integration/test_validate_e2e.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_validate_e2e.py
git commit -m "test: end-to-end model validation integration test"
```

---

## Phase 11: Full Suite Verification

### Task 12: Run full test suite and verify

**Step 1: Run all tests**

Run: `py -m pytest --tb=short -q`
Expected: All tests pass (245+ tests), 0 failures

**Step 2: Commit any fixes if needed**

---
