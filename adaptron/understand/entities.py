from __future__ import annotations

import re

from adaptron.core.registry import register_plugin
from adaptron.understand.models import Entity

PATTERNS = {
    "EMAIL": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    "DATE": r"\b\d{4}[-/]\d{2}[-/]\d{2}\b",
    "MONEY": r"\$[\d,]+\.?\d*",
    "URL": r"https?://[^\s]+",
    "PHONE": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
}


@register_plugin("analyzer", "entity_extractor")
class RegexEntityExtractor:
    def __init__(self, extra_patterns: dict[str, str] | None = None) -> None:
        self.patterns = {**PATTERNS}
        if extra_patterns:
            self.patterns.update(extra_patterns)

    def extract(self, text: str) -> list[Entity]:
        entities = []
        for label, pattern in self.patterns.items():
            for match in re.finditer(pattern, text):
                entities.append(
                    Entity(
                        text=match.group(),
                        label=label,
                        start=match.start(),
                        end=match.end(),
                    )
                )
        return entities
