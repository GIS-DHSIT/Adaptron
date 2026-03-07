"""Mapping validator for column mapping against data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adaptron.ingest.models import RawDocument


@dataclass
class ValidationError:
    record_index: int
    field: str
    error_type: str  # "missing_column", "null_value", "type_mismatch"
    raw_value: Any
    suggestion: str


@dataclass
class ValidationReport:
    total_records: int
    valid_records: int
    invalid_records: int
    coverage_pct: float
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    approved: bool = False


class MappingValidator:
    """Validates a column mapping against data records."""

    def validate(
        self,
        mapping: dict[str, str],
        data: list[RawDocument],
        format_name: str,
    ) -> ValidationReport:
        """Validate mapping against data and return a report.

        Data is accessed via doc.metadata["row"][column_name].
        """
        total = len(data)
        errors: list[ValidationError] = []
        warnings: list[str] = []
        invalid_indices: set[int] = set()

        for i, doc in enumerate(data):
            row = doc.metadata.get("row", {})
            for source_col, target_col in mapping.items():
                # Check if column exists in this record
                if source_col not in row:
                    errors.append(ValidationError(
                        record_index=i,
                        field=source_col,
                        error_type="missing_column",
                        raw_value=None,
                        suggestion=f"Column '{source_col}' not found in record. Available: {list(row.keys())}",
                    ))
                    invalid_indices.add(i)
                elif row[source_col] is None:
                    errors.append(ValidationError(
                        record_index=i,
                        field=source_col,
                        error_type="null_value",
                        raw_value=None,
                        suggestion=f"Column '{source_col}' has null value. Consider filtering or providing a default.",
                    ))
                    invalid_indices.add(i)

        valid = total - len(invalid_indices)
        invalid = len(invalid_indices)
        coverage = (valid / total * 100.0) if total > 0 else 0.0

        # Approval gates
        if coverage == 100.0:
            approved = True
        elif coverage >= 99.0:
            approved = True
            warnings.append(
                f"Coverage is {coverage:.1f}% — auto-approved with notification. "
                f"{invalid} record(s) have issues."
            )
        elif coverage >= 95.0:
            approved = False
            warnings.append(
                f"Coverage is {coverage:.1f}% — needs explicit approval. "
                f"{invalid} record(s) have issues."
            )
        else:
            approved = False
            warnings.append(
                f"Coverage is {coverage:.1f}% — blocked. "
                f"Too many invalid records ({invalid}/{total})."
            )

        return ValidationReport(
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            coverage_pct=coverage,
            errors=errors,
            warnings=warnings,
            approved=approved,
        )
