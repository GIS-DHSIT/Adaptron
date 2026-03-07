from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.understand.models import Chunk

QUESTION_TEMPLATES = [
    "What is {topic}?",
    "Can you explain {topic}?",
    "Describe {topic}.",
    "What do you know about {topic}?",
]


@register_plugin("synthesizer", "qa")
class QAPairSynthesizer(BaseSynthesizer):
    def __init__(self, templates: list[str] | None = None) -> None:
        self.templates = templates or QUESTION_TEMPLATES

    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            topic = chunk.content[:80].rstrip(".").strip()
            template = self.templates[i % len(self.templates)]
            question = template.format(topic=topic)
            pairs.append({
                "question": question,
                "answer": chunk.content,
                "source_ref": chunk.source_ref,
                "chunk_index": chunk.chunk_index,
            })
        return pairs
