"""Schema inference analyzer for generating natural language descriptions from database schemas."""

from __future__ import annotations

import re

from adaptron.core.registry import register_plugin
from adaptron.ingest.models import RawDocument
from adaptron.understand.base import BaseAnalyzer
from adaptron.understand.models import AnalyzedCorpus


@register_plugin("analyzer", "schema_inferrer")
class SchemaInferenceAnalyzer(BaseAnalyzer):
    """Generates natural language descriptions from database table schemas."""

    def analyze(self, documents: list[RawDocument]) -> AnalyzedCorpus:
        sql_docs = [d for d in documents if d.source_ref.startswith("sql://")]
        descriptions: dict[str, str] = {}
        for doc in sql_docs:
            table_name = doc.source_ref.removeprefix("sql://")
            descriptions[table_name] = self.describe_table(doc)
        return AnalyzedCorpus(schema_descriptions=descriptions)

    def describe_table(self, doc: RawDocument) -> str:
        """Generate a human-readable description of a database table from its schema text."""
        content = doc.content
        table_name = self._parse_table_name(content)
        columns = self._parse_columns(content)
        foreign_keys = self._parse_foreign_keys(content)

        parts: list[str] = []

        # Table purpose sentence
        parts.append(
            f"The '{table_name}' table stores records with "
            f"{len(columns)} column(s)."
        )

        # Column descriptions
        if columns:
            col_parts = []
            for col_name, col_type in columns:
                col_parts.append(f"'{col_name}' ({col_type})")
            parts.append("Columns: " + ", ".join(col_parts) + ".")

        # Foreign key relationships
        if foreign_keys:
            fk_parts = []
            for constrained, referred_table, referred_cols in foreign_keys:
                fk_parts.append(
                    f"{constrained} references '{referred_table}' ({referred_cols})"
                )
            parts.append("Relationships: " + "; ".join(fk_parts) + ".")

        return " ".join(parts)

    @staticmethod
    def _parse_table_name(content: str) -> str:
        match = re.search(r"^Table:\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else "unknown"

    @staticmethod
    def _parse_columns(content: str) -> list[tuple[str, str]]:
        columns: list[tuple[str, str]] = []
        for match in re.finditer(
            r"^\s+-\s+(\S+)\s+\(([^)]+)\)", content, re.MULTILINE
        ):
            # Only capture column lines (not FK lines which contain "->")
            line_start = content.rfind("\n", 0, match.start()) + 1
            line = content[line_start : match.end()]
            if "->" not in line:
                columns.append((match.group(1), match.group(2)))
        return columns

    @staticmethod
    def _parse_foreign_keys(content: str) -> list[tuple[str, str, str]]:
        fks: list[tuple[str, str, str]] = []
        fk_section = re.search(
            r"Foreign Keys:\n((?:\s+-\s+.+\n?)+)", content
        )
        if not fk_section:
            return fks
        fk_text = fk_section.group(1)
        for match in re.finditer(
            r"\s+-\s+(.+?)\s*->\s*(\S+?)\.(\S+)", fk_text
        ):
            fks.append((match.group(1).strip(), match.group(2), match.group(3)))
        return fks
