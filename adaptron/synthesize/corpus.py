from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.understand.models import Chunk


@register_plugin("synthesizer", "corpus")
class CorpusSynthesizer(BaseSynthesizer):
    def __init__(self, separator: str = "\n\n") -> None:
        self.separator = separator

    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        if not chunks:
            return []
        text = self.separator.join(chunk.content for chunk in chunks)
        return [{
            "text": text,
            "source_refs": [chunk.source_ref for chunk in chunks],
            "num_chunks": len(chunks),
        }]
