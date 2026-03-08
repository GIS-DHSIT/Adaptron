from __future__ import annotations

import json
import statistics
from typing import Any

from adaptron.validate.config import ValidationConfig
from adaptron.validate.models import ReadinessResult


class ProductionReadiness:
    """Check production readiness of a fine-tuned model."""

    def __init__(self, config: ValidationConfig | None = None) -> None:
        self.config = config or ValidationConfig(model_path="")

    def compute_latency_stats(self, durations_ms: list[float]) -> dict[str, float]:
        """Compute p50, p95, p99, and mean latency from durations in ms."""
        if not durations_ms:
            return {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "mean_ms": 0.0}
        sorted_d = sorted(durations_ms)
        n = len(sorted_d)

        def percentile(pct: float) -> float:
            k = (pct / 100.0) * (n - 1)
            f = int(k)
            c = f + 1 if f + 1 < n else f
            d = k - f
            return sorted_d[f] + d * (sorted_d[c] - sorted_d[f])

        return {
            "p50_ms": round(percentile(50), 2),
            "p95_ms": round(percentile(95), 2),
            "p99_ms": round(percentile(99), 2),
            "mean_ms": round(statistics.mean(durations_ms), 2),
        }

    def check_consistency(self, responses_per_prompt: list[list[str]]) -> float:
        """Check response consistency via pairwise exact match ratio."""
        if not responses_per_prompt:
            return 1.0
        scores: list[float] = []
        for responses in responses_per_prompt:
            if len(responses) < 2:
                scores.append(1.0)
                continue
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
        self,
        expected_formats: list[str],
        actual_outputs: list[str],
    ) -> float:
        """Check format compliance for json, list, or text formats."""
        if not expected_formats:
            return 1.0
        compliant = 0
        for fmt, output in zip(expected_formats, actual_outputs):
            fmt_lower = fmt.strip().lower()
            if fmt_lower == "json":
                try:
                    json.loads(output)
                    compliant += 1
                except (json.JSONDecodeError, ValueError):
                    pass
            elif fmt_lower == "list":
                if "\n" in output.strip() or output.strip().startswith("-") or output.strip().startswith("*"):
                    compliant += 1
            else:
                # text format: anything non-empty passes
                if output.strip():
                    compliant += 1
        return compliant / len(expected_formats)

    def run(
        self,
        durations_ms: list[float] | None = None,
        responses_per_prompt: list[list[str]] | None = None,
        expected_formats: list[str] | None = None,
        actual_outputs: list[str] | None = None,
        edge_case_results: list[dict[str, Any]] | None = None,
    ) -> ReadinessResult:
        """Run full production readiness checks."""
        latency = self.compute_latency_stats(durations_ms or [])
        consistency = self.check_consistency(responses_per_prompt or [])
        compliance = self.check_format_compliance(
            expected_formats or [], actual_outputs or []
        )

        checks: dict[str, str] = {}
        thresholds = self.config.thresholds
        consistency_thresh = thresholds.get("consistency", {"pass": 0.85, "warning": 0.7})
        if consistency >= consistency_thresh["pass"]:
            checks["consistency"] = "pass"
        elif consistency >= consistency_thresh["warning"]:
            checks["consistency"] = "warning"
        else:
            checks["consistency"] = "fail"

        return ReadinessResult(
            latency=latency,
            consistency_score=consistency,
            edge_case_results=edge_case_results or [],
            format_compliance=compliance,
            checks=checks,
        )
