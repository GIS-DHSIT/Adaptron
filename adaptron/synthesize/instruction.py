from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.understand.models import Chunk

TEMPLATES = [
    ("Explain the following concept:\n{context}", "{context}"),
    ("Summarize this information:\n{context}", "{context}"),
    ("Based on the following, answer any questions:\n{context}", "{context}"),
    ("What are the key points in:\n{context}", "{context}"),
]


@register_plugin("synthesizer", "instruction")
class TemplateInstructionGenerator(BaseSynthesizer):
    def __init__(self, templates: list[tuple[str, str]] | None = None) -> None:
        self.templates = templates or TEMPLATES

    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        pairs = []
        for i, chunk in enumerate(chunks):
            template = self.templates[i % len(self.templates)]
            instruction = template[0].format(context=chunk.content[:200])
            response = chunk.content
            pairs.append({
                "instruction": instruction,
                "response": response,
                "source_ref": chunk.source_ref,
                "chunk_index": chunk.chunk_index,
            })
        return pairs
