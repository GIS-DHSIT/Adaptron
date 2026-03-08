from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.validate.benchmark import BenchmarkSuite
from adaptron.validate.comparator import ModelComparator
from adaptron.validate.config import ValidationConfig
from adaptron.validate.hallucination import HallucinationDetector
from adaptron.validate.models import ValidationReport
from adaptron.validate.readiness import ProductionReadiness
from adaptron.validate.report import ReportGenerator


class ValidationEngine:
    """Orchestrate all validation steps and produce a final report."""

    def __init__(
        self,
        config: ValidationConfig | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.config = config or ValidationConfig(model_path="")
        self.event_bus = event_bus or EventBus()
        self.benchmark_suite = BenchmarkSuite(self.config)
        self.comparator = ModelComparator(self.config)
        self.readiness = ProductionReadiness(self.config)
        self.hallucination = HallucinationDetector(self.config)
        self.reporter = ReportGenerator(self.config.output_dir)

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.event_bus.emit(event_type, Event(type=event_type, data=data))

    def compute_overall_grade(
        self,
        benchmark_grade: str,
        hallucination_rate: float,
        improvement_pct: float | None = None,
    ) -> str:
        grade_order = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
        thresholds = self.config.thresholds

        # Benchmark score
        benchmark_score = grade_order.get(benchmark_grade, 0)

        # Hallucination score
        hall_thresh = thresholds.get("hallucination_rate", {"pass": 0.05, "warning": 0.15})
        if hallucination_rate < hall_thresh["pass"]:
            hall_score = 4
        elif hallucination_rate < hall_thresh["warning"]:
            hall_score = 2
        else:
            hall_score = 0

        # Improvement score
        if improvement_pct is None:
            imp_score = 3
        else:
            imp_thresh = thresholds.get("improvement_pct", {"pass": 20.0, "warning": 5.0})
            if improvement_pct >= imp_thresh["pass"]:
                imp_score = 4
            elif improvement_pct >= imp_thresh["warning"]:
                imp_score = 2
            else:
                imp_score = 0

        avg = (benchmark_score + hall_score + imp_score) / 3.0

        if avg >= 3.5:
            return "A"
        elif avg >= 2.5:
            return "B"
        elif avg >= 1.5:
            return "C"
        elif avg >= 0.5:
            return "D"
        return "F"

    def generate_summary(
        self,
        overall_grade: str,
        benchmark_grade: str,
        hallucination_rate: float,
        improvement_pct: float | None = None,
    ) -> str:
        parts = [f"Overall grade: {overall_grade}."]
        parts.append(f"Benchmark grade: {benchmark_grade}.")
        parts.append(f"Hallucination rate: {hallucination_rate:.2%}.")
        if improvement_pct is not None:
            parts.append(f"Improvement over baseline: {improvement_pct:.1f}%.")
        else:
            parts.append("No baseline comparison performed.")

        if overall_grade in ("A", "B"):
            parts.append("Model is recommended for production deployment.")
        elif overall_grade == "C":
            parts.append("Model may need further fine-tuning before production use.")
        else:
            parts.append("Model is not recommended for production deployment.")

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
        model_info = model_info or {}
        self._emit("validation.started", {"model_info": model_info})

        # Benchmark
        self._emit("validation.benchmark.started", {})
        benchmark_result = self.benchmark_suite.run(predictions, references, test_data)
        self._emit("validation.benchmark.completed", {"grade": benchmark_result.grade})

        # Comparison
        comparison_result = None
        improvement_pct: float | None = None
        if baseline_preds is not None and prompts is not None:
            self._emit("validation.comparison.started", {})
            baseline_metrics = self.benchmark_suite.compute_metrics(
                baseline_preds, references, benchmark_result.task_type
            )
            comparison_result = self.comparator.run(
                prompts, baseline_preds, predictions, references,
                baseline_metrics=baseline_metrics,
                finetuned_metrics=benchmark_result.metrics,
            )
            if comparison_result.improvement_pct:
                improvement_pct = sum(comparison_result.improvement_pct.values()) / len(
                    comparison_result.improvement_pct
                )
            self._emit("validation.comparison.completed", {
                "wins": comparison_result.wins,
                "losses": comparison_result.losses,
            })

        # Readiness
        self._emit("validation.readiness.started", {})
        readiness_result = self.readiness.run(
            durations_ms=latency_durations_ms,
            responses_per_prompt=responses_per_prompt,
        )
        self._emit("validation.readiness.completed", {"checks": readiness_result.checks})

        # Hallucination
        self._emit("validation.hallucination.started", {})
        hallucination_result = self.hallucination.run(
            predictions=predictions,
            references=references,
            responses_per_prompt=responses_per_prompt,
        )
        self._emit("validation.hallucination.completed", {
            "rate": hallucination_result.hallucination_rate,
        })

        # Overall grade and summary
        overall_grade = self.compute_overall_grade(
            benchmark_result.grade,
            hallucination_result.hallucination_rate,
            improvement_pct,
        )
        summary = self.generate_summary(
            overall_grade, benchmark_result.grade,
            hallucination_result.hallucination_rate, improvement_pct,
        )

        report = ValidationReport(
            model_info=model_info,
            benchmark=benchmark_result,
            comparison=comparison_result,
            readiness=readiness_result,
            hallucination=hallucination_result,
            overall_grade=overall_grade,
            summary=summary,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Generate reports
        self._emit("validation.report.started", {})
        self.reporter.generate(report)
        self._emit("validation.report.completed", {"overall_grade": overall_grade})

        self._emit("validation.completed", {"overall_grade": overall_grade})
        return report
