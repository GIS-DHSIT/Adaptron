"""Training format auto-detector using rule-based heuristics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adaptron.connectors.models import DataSchema


@dataclass
class FormatRecommendation:
    primary_format: str  # "qa", "instruction", "dpo", "chat", "text2sql", "corpus"
    confidence: float  # 0.0 to 1.0
    alternatives: list[str] = field(default_factory=list)
    column_mapping: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""


class TrainingFormatDetector:
    """Rule-based heuristic detector for training data formats."""

    def detect(self, schema: DataSchema, samples: list[Any]) -> FormatRecommendation:
        """Analyze schema column names and structure to recommend a training format."""
        candidates: list[FormatRecommendation] = []

        # Check each detection rule in priority order
        candidates.append(self._check_dpo(schema))
        candidates.append(self._check_qa(schema))
        candidates.append(self._check_instruction(schema))
        candidates.append(self._check_chat(schema))
        candidates.append(self._check_text2sql(schema))
        candidates.append(self._check_corpus(schema))

        # Sort by confidence descending
        candidates.sort(key=lambda r: r.confidence, reverse=True)

        best = candidates[0]
        alternatives = [
            c.primary_format for c in candidates[1:]
            if c.confidence > 0.3 and c.primary_format != best.primary_format
        ]
        best.alternatives = alternatives

        # Fallback: if confidence is too low, default to corpus
        if best.confidence < 0.4:
            return FormatRecommendation(
                primary_format="corpus",
                confidence=best.confidence,
                alternatives=[c.primary_format for c in candidates if c.primary_format != "corpus"],
                column_mapping={},
                reasoning=f"No strong pattern detected (best match: {best.primary_format} at {best.confidence:.2f}). Falling back to corpus format.",
            )

        return best

    def _get_field_names(self, schema: DataSchema) -> list[set[str]]:
        """Get field name sets for each collection."""
        return [
            {f.name.lower() for f in col.fields}
            for col in schema.collections
        ]

    def _check_qa(self, schema: DataSchema) -> FormatRecommendation:
        for col in schema.collections:
            names = {f.name.lower() for f in col.fields}
            if "question" in names and "answer" in names:
                mapping = {"question": "input", "answer": "output"}
                return FormatRecommendation(
                    primary_format="qa",
                    confidence=0.95,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has question/answer columns, indicating QA format.",
                )
            if "query" in names and "answer" in names:
                mapping = {"query": "input", "answer": "output"}
                return FormatRecommendation(
                    primary_format="qa",
                    confidence=0.85,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has query/answer columns, suggesting QA format.",
                )
        return FormatRecommendation(primary_format="qa", confidence=0.0, reasoning="No QA pattern found.")

    def _check_instruction(self, schema: DataSchema) -> FormatRecommendation:
        for col in schema.collections:
            names = {f.name.lower() for f in col.fields}
            if "instruction" in names and ("output" in names or "response" in names):
                target = "output" if "output" in names else "response"
                mapping = {"instruction": "instruction", target: "response"}
                return FormatRecommendation(
                    primary_format="instruction",
                    confidence=0.95,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has instruction/{target} columns.",
                )
            if "prompt" in names and "response" in names and "chosen" not in names:
                mapping = {"prompt": "instruction", "response": "response"}
                return FormatRecommendation(
                    primary_format="instruction",
                    confidence=0.85,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has prompt/response columns.",
                )
        return FormatRecommendation(primary_format="instruction", confidence=0.0, reasoning="No instruction pattern found.")

    def _check_dpo(self, schema: DataSchema) -> FormatRecommendation:
        for col in schema.collections:
            names = {f.name.lower() for f in col.fields}
            if "prompt" in names and "chosen" in names and "rejected" in names:
                mapping = {"prompt": "prompt", "chosen": "chosen", "rejected": "rejected"}
                return FormatRecommendation(
                    primary_format="dpo",
                    confidence=0.95,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has prompt/chosen/rejected columns, indicating DPO preference format.",
                )
        return FormatRecommendation(primary_format="dpo", confidence=0.0, reasoning="No DPO pattern found.")

    def _check_chat(self, schema: DataSchema) -> FormatRecommendation:
        for col in schema.collections:
            names = {f.name.lower() for f in col.fields}
            if "role" in names and "content" in names and "session_id" in names:
                mapping = {"role": "role", "content": "content", "session_id": "session_id"}
                return FormatRecommendation(
                    primary_format="chat",
                    confidence=0.95,
                    column_mapping=mapping,
                    reasoning=f"Collection '{col.name}' has role/content/session_id columns, indicating chat format.",
                )
            if "role" in names and "content" in names:
                mapping = {"role": "role", "content": "content"}
                return FormatRecommendation(
                    primary_format="chat",
                    confidence=0.7,
                    column_mapping=mapping,
                    reasoning=f"Collection '{col.name}' has role/content but no session_id.",
                )
        return FormatRecommendation(primary_format="chat", confidence=0.0, reasoning="No chat pattern found.")

    def _check_text2sql(self, schema: DataSchema) -> FormatRecommendation:
        tables = [c for c in schema.collections if c.source_type == "table"]
        has_relationships = any(len(c.relationships) > 0 for c in schema.collections)

        if len(tables) >= 3 and has_relationships:
            return FormatRecommendation(
                primary_format="text2sql",
                confidence=0.9,
                column_mapping={"schema": "context"},
                reasoning=f"Database has {len(tables)} tables with relationships, suitable for text2sql.",
            )
        if len(tables) >= 3:
            return FormatRecommendation(
                primary_format="text2sql",
                confidence=0.6,
                column_mapping={"schema": "context"},
                reasoning=f"Database has {len(tables)} tables but no explicit relationships.",
            )
        return FormatRecommendation(primary_format="text2sql", confidence=0.0, reasoning="Not enough tables for text2sql.")

    def _check_corpus(self, schema: DataSchema) -> FormatRecommendation:
        text_field_names = {"title", "body", "text", "content", "description", "summary", "abstract", "document"}
        for col in schema.collections:
            names = {f.name.lower() for f in col.fields}
            text_fields = names & text_field_names
            if len(text_fields) >= 2:
                mapping = {f: "text" for f in text_fields}
                return FormatRecommendation(
                    primary_format="corpus",
                    confidence=0.8,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has text fields ({', '.join(text_fields)}), suitable for corpus format.",
                )
            if len(text_fields) == 1:
                mapping = {list(text_fields)[0]: "text"}
                return FormatRecommendation(
                    primary_format="corpus",
                    confidence=0.5,
                    column_mapping=mapping,
                    reasoning=f"Table '{col.name}' has a single text field ({list(text_fields)[0]}).",
                )
        return FormatRecommendation(
            primary_format="corpus",
            confidence=0.2,
            column_mapping={},
            reasoning="No recognized text fields; corpus is the fallback.",
        )
