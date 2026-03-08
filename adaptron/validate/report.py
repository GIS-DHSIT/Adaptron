from __future__ import annotations

import dataclasses
import json
import os
from typing import Any

from adaptron.validate.models import ValidationReport

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Validation Report — {{ report.model_info.get("name", "Unknown Model") }}</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 900px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.6; }
  h1 { border-bottom: 2px solid #eee; padding-bottom: 10px; }
  h2 { margin-top: 30px; color: #555; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background: #f5f5f5; }
  .grade { font-size: 48px; font-weight: bold; margin: 10px 0; }
  .grade-A { color: #2e7d32; }
  .grade-B { color: #1565c0; }
  .grade-C { color: #f9a825; }
  .grade-D { color: #ef6c00; }
  .grade-F { color: #c62828; }
  .summary { background: #f9f9f9; padding: 15px; border-radius: 6px; margin: 15px 0; }
  .section { margin-bottom: 30px; }
</style>
</head>
<body>
<h1>Validation Report</h1>
<p><strong>Model:</strong> {{ report.model_info.get("name", "Unknown") }}</p>
<p><strong>Base Model:</strong> {{ report.model_info.get("base_model", "N/A") }}</p>
<p><strong>Timestamp:</strong> {{ report.timestamp }}</p>

<div class="grade grade-{{ report.overall_grade }}">Grade: {{ report.overall_grade }}</div>

<div class="summary">{{ report.summary }}</div>

{% if report.benchmark %}
<div class="section">
<h2>Benchmark Results</h2>
<p><strong>Task Type:</strong> {{ report.benchmark.task_type }} | <strong>Grade:</strong> {{ report.benchmark.grade }}</p>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{% for key, value in report.benchmark.metrics.items() %}
<tr><td>{{ key }}</td><td>{{ "%.4f"|format(value) }}</td></tr>
{% endfor %}
</table>
</div>
{% endif %}

{% if report.comparison %}
<div class="section">
<h2>Comparison Results</h2>
<p><strong>Wins:</strong> {{ report.comparison.wins }} |
   <strong>Losses:</strong> {{ report.comparison.losses }} |
   <strong>Ties:</strong> {{ report.comparison.ties }}</p>
{% if report.comparison.improvement_pct %}
<table>
<tr><th>Metric</th><th>Improvement %</th></tr>
{% for key, value in report.comparison.improvement_pct.items() %}
<tr><td>{{ key }}</td><td>{{ "%.2f"|format(value) }}%</td></tr>
{% endfor %}
</table>
{% endif %}
</div>
{% endif %}

{% if report.readiness %}
<div class="section">
<h2>Production Readiness</h2>
<table>
<tr><th>Latency Metric</th><th>Value (ms)</th></tr>
{% for key, value in report.readiness.latency.items() %}
<tr><td>{{ key }}</td><td>{{ "%.2f"|format(value) }}</td></tr>
{% endfor %}
</table>
<p><strong>Consistency Score:</strong> {{ "%.4f"|format(report.readiness.consistency_score) }}</p>
<p><strong>Format Compliance:</strong> {{ "%.4f"|format(report.readiness.format_compliance) }}</p>
<table>
<tr><th>Check</th><th>Status</th></tr>
{% for key, value in report.readiness.checks.items() %}
<tr><td>{{ key }}</td><td>{{ value }}</td></tr>
{% endfor %}
</table>
</div>
{% endif %}

{% if report.hallucination %}
<div class="section">
<h2>Hallucination Detection</h2>
<p><strong>Mode:</strong> {{ report.hallucination.mode }}</p>
<p><strong>Hallucination Rate:</strong> {{ "%.4f"|format(report.hallucination.hallucination_rate) }}</p>
{% if report.hallucination.faithfulness_score is not none %}
<p><strong>Faithfulness Score:</strong> {{ "%.4f"|format(report.hallucination.faithfulness_score) }}</p>
{% endif %}
{% if report.hallucination.consistency_score is not none %}
<p><strong>Consistency Score:</strong> {{ "%.4f"|format(report.hallucination.consistency_score) }}</p>
{% endif %}
{% if report.hallucination.flagged_samples %}
<p><strong>Flagged Samples:</strong> {{ report.hallucination.flagged_samples|length }}</p>
{% endif %}
</div>
{% endif %}

</body>
</html>
"""


class ReportGenerator:
    """Generate JSON and HTML validation reports."""

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _report_to_dict(report: ValidationReport) -> dict[str, Any]:
        return dataclasses.asdict(report)

    def generate_json(self, report: ValidationReport) -> str:
        data = self._report_to_dict(report)
        path = os.path.join(self.output_dir, "report.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return path

    def generate_html(self, report: ValidationReport) -> str:
        try:
            from jinja2 import Template
        except ImportError:
            # Fallback: simple string replacement
            html = self._fallback_html(report)
            path = os.path.join(self.output_dir, "report.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return path

        template = Template(HTML_TEMPLATE)
        html = template.render(report=report)
        path = os.path.join(self.output_dir, "report.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def _fallback_html(self, report: ValidationReport) -> str:
        """Simple HTML fallback when Jinja2 is not available."""
        model_name = report.model_info.get("name", "Unknown")
        grade = report.overall_grade
        grade_colors = {"A": "#2e7d32", "B": "#1565c0", "C": "#f9a825", "D": "#ef6c00", "F": "#c62828"}
        color = grade_colors.get(grade, "#333")

        parts = [
            "<!DOCTYPE html><html><head><meta charset='UTF-8'>",
            "<style>body{font-family:sans-serif;max-width:900px;margin:40px auto;padding:0 20px;}</style>",
            f"<title>Validation Report - {model_name}</title></head><body>",
            f"<h1>Validation Report</h1>",
            f"<p><strong>Model:</strong> {model_name}</p>",
            f"<p><strong>Timestamp:</strong> {report.timestamp}</p>",
            f"<div style='font-size:48px;font-weight:bold;color:{color}'>Grade: {grade}</div>",
            f"<p>{report.summary}</p>",
        ]

        if report.benchmark:
            parts.append(f"<h2>Benchmark Results</h2>")
            parts.append(f"<p>Task: {report.benchmark.task_type}, Grade: {report.benchmark.grade}</p>")
            for k, v in report.benchmark.metrics.items():
                parts.append(f"<p>{k}: {v:.4f}</p>")

        if report.readiness:
            parts.append(f"<h2>Production Readiness</h2>")
            for k, v in report.readiness.checks.items():
                parts.append(f"<p>{k}: {v}</p>")

        if report.hallucination:
            parts.append(f"<h2>Hallucination Detection</h2>")
            parts.append(f"<p>Rate: {report.hallucination.hallucination_rate:.4f}</p>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def generate(self, report: ValidationReport) -> tuple[str, str]:
        json_path = self.generate_json(report)
        html_path = self.generate_html(report)
        return json_path, html_path
