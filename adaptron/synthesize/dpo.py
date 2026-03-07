from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.understand.models import Chunk

PROMPT_TEMPLATES = [
    "Explain {topic}.",
    "What is {topic}?",
    "Describe {topic} in detail.",
    "Provide information about {topic}.",
]

REJECTED_TEMPLATE = "I'm not sure about that topic. Can you be more specific?"


@register_plugin("synthesizer", "dpo")
class DPOPreferenceSynthesizer(BaseSynthesizer):
    def __init__(
        self,
        prompt_templates: list[str] | None = None,
        rejected_response: str | None = None,
    ) -> None:
        self.prompt_templates = prompt_templates or PROMPT_TEMPLATES
        self.rejected_response = rejected_response or REJECTED_TEMPLATE

    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            topic = chunk.content[:80].rstrip(".").strip()
            template = self.prompt_templates[i % len(self.prompt_templates)]
            prompt = template.format(topic=topic)
            pairs.append({
                "prompt": prompt,
                "chosen": chunk.content,
                "rejected": self.rejected_response,
                "source_ref": chunk.source_ref,
                "chunk_index": chunk.chunk_index,
            })
        return pairs
