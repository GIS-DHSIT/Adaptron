from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.understand.models import Chunk

QUESTION_TEMPLATES = [
    "Show all records from {table}.",
    "How many rows are in {table}?",
    "List everything in the {table} table.",
]

SQL_TEMPLATES = [
    "SELECT * FROM {table};",
    "SELECT COUNT(*) FROM {table};",
    "SELECT * FROM {table};",
]


@register_plugin("synthesizer", "text2sql")
class Text2SQLSynthesizer(BaseSynthesizer):
    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            table_name = chunk.metadata.get("table_name", "")
            if not table_name:
                # Try to extract a table name from content
                table_name = self._extract_table_name(chunk.content)
            idx = i % len(QUESTION_TEMPLATES)
            question = QUESTION_TEMPLATES[idx].format(table=table_name)
            sql = SQL_TEMPLATES[idx].format(table=table_name)
            pairs.append({
                "question": question,
                "sql": sql,
                "source_ref": chunk.source_ref,
                "chunk_index": chunk.chunk_index,
            })
        return pairs

    @staticmethod
    def _extract_table_name(content: str) -> str:
        """Best-effort extraction of a table name from content."""
        # Look for common patterns like "CREATE TABLE <name>" or "table <name>"
        lower = content.lower()
        for keyword in ("create table ", "table "):
            pos = lower.find(keyword)
            if pos != -1:
                rest = content[pos + len(keyword):].strip().split()[0]
                return rest.strip("(").strip("`").strip('"')
        # Fallback: use the first word
        first_word = content.split()[0] if content.strip() else "unknown"
        return first_word
