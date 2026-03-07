from __future__ import annotations

from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.understand.models import Chunk

SYSTEM_PROMPT = "You are a helpful assistant that provides accurate information."

USER_TEMPLATES = [
    "Tell me about {topic}.",
    "Can you explain {topic}?",
    "What can you tell me about {topic}?",
    "I'd like to learn about {topic}.",
]


@register_plugin("synthesizer", "chat")
class ChatConversationSynthesizer(BaseSynthesizer):
    def __init__(
        self,
        system_prompt: str | None = None,
        user_templates: list[str] | None = None,
    ) -> None:
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.user_templates = user_templates or USER_TEMPLATES

    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        conversations: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            topic = chunk.content[:80].rstrip(".").strip()
            template = self.user_templates[i % len(self.user_templates)]
            user_msg = template.format(topic=topic)
            conversations.append({
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": chunk.content},
                ],
                "source_ref": chunk.source_ref,
                "chunk_index": chunk.chunk_index,
            })
        return conversations
