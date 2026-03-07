"""Playground engine for interacting with finetuned models via Ollama."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    done: bool = True
    total_duration_ns: int = 0
    eval_count: int = 0


@dataclass
class CompareResult:
    responses: dict[str, ChatResponse] = field(default_factory=dict)


class PlaygroundEngine:
    """Interact with finetuned models via the Ollama HTTP API."""

    def __init__(self, ollama_url: str = OLLAMA_BASE_URL) -> None:
        self.ollama_url = ollama_url.rstrip("/")

    async def list_models(self) -> list[dict[str, Any]]:
        """List available Ollama models, optionally filtered to adaptron-* ones."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.ollama_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])

    async def list_adaptron_models(self) -> list[dict[str, Any]]:
        """List only models created by Adaptron (adaptron-* prefix)."""
        all_models = await self.list_models()
        return [m for m in all_models if m.get("name", "").startswith("adaptron-")]

    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> ChatResponse:
        """Send a chat request to Ollama and return the full response."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{self.ollama_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return ChatResponse(
                content=data.get("message", {}).get("content", ""),
                model=model,
                done=data.get("done", True),
                total_duration_ns=data.get("total_duration", 0),
                eval_count=data.get("eval_count", 0),
            )

    async def chat_stream(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat response tokens from Ollama."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", f"{self.ollama_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            return

    async def chat_with_rag(
        self,
        model: str,
        messages: list[ChatMessage],
        collection_name: str = "default",
        persist_dir: str = "./chroma_db",
        top_k: int = 5,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> ChatResponse | AsyncIterator[str]:
        """Chat with RAG context injected into the system prompt."""
        from adaptron.rag.retriever import ChromaRetriever

        # Get the last user message for retrieval query
        user_messages = [m for m in messages if m.role == "user"]
        if not user_messages:
            if stream:
                return self.chat_stream(model, messages, temperature, max_tokens)
            return await self.chat(model, messages, temperature, max_tokens)

        query = user_messages[-1].content
        retriever = ChromaRetriever(persist_dir=persist_dir)
        try:
            chunks = retriever.retrieve(query, collection_name=collection_name, top_k=top_k)
        except Exception as e:
            logger.warning("RAG retrieval failed: %s. Proceeding without context.", e)
            chunks = []

        # Build RAG-augmented messages
        rag_messages = list(messages)
        if chunks:
            context = "\n\n---\n\n".join(c.content for c in chunks)
            rag_system = ChatMessage(
                role="system",
                content=f"Use the following context to help answer the user's question. "
                        f"If the context doesn't contain relevant information, answer based on your training.\n\n"
                        f"Context:\n{context}",
            )
            # Insert RAG system message at the beginning
            rag_messages = [rag_system] + rag_messages

        if stream:
            return self.chat_stream(model, rag_messages, temperature, max_tokens)
        return await self.chat(model, rag_messages, temperature, max_tokens)

    async def compare(
        self,
        models: list[str],
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> CompareResult:
        """Run the same prompt against multiple models in parallel."""
        async def _run(model: str) -> tuple[str, ChatResponse]:
            resp = await self.chat(model, messages, temperature, max_tokens)
            return model, resp

        tasks = [_run(m) for m in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        compare_result = CompareResult()
        for r in results:
            if isinstance(r, Exception):
                logger.error("Model comparison failed: %s", r)
            else:
                model_name, response = r
                compare_result.responses[model_name] = response

        return compare_result
