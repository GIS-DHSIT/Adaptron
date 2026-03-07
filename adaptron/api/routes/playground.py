"""Playground API routes for testing finetuned models."""

from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from adaptron.playground.engine import PlaygroundEngine, ChatMessage, ChatResponse

router = APIRouter(prefix="/api/playground", tags=["playground"])

# Shared engine instance
_engine = PlaygroundEngine()


class ChatRequest(BaseModel):
    model: str
    messages: list[dict[str, str]]  # [{"role": "user", "content": "..."}]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = True
    rag_enabled: bool = False
    rag_collection: str = "default"
    rag_top_k: int = 5


class CompareRequest(BaseModel):
    models: list[str]
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 2048


class ModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class CompareResponseModel(BaseModel):
    responses: dict[str, dict[str, str | int | bool]]


@router.get("/models", response_model=list[ModelInfo])
async def list_models(adaptron_only: bool = False):
    """List available Ollama models."""
    try:
        if adaptron_only:
            models = await _engine.list_adaptron_models()
        else:
            models = await _engine.list_models()
        return [
            ModelInfo(
                name=m.get("name", ""),
                size=m.get("size"),
                modified_at=m.get("modified_at"),
            )
            for m in models
        ]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {e}")


@router.post("/chat")
async def chat(req: ChatRequest):
    """Chat with a model. Supports streaming SSE and non-streaming JSON."""
    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in req.messages]

    if req.stream:
        async def event_stream() -> AsyncIterator[str]:
            try:
                if req.rag_enabled:
                    stream_iter = await _engine.chat_with_rag(
                        model=req.model,
                        messages=messages,
                        collection_name=req.rag_collection,
                        top_k=req.rag_top_k,
                        temperature=req.temperature,
                        max_tokens=req.max_tokens,
                        stream=True,
                    )
                else:
                    stream_iter = _engine.chat_stream(
                        model=req.model,
                        messages=messages,
                        temperature=req.temperature,
                        max_tokens=req.max_tokens,
                    )
                async for token in stream_iter:
                    yield f"data: {json.dumps({'token': token})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    else:
        try:
            if req.rag_enabled:
                result = await _engine.chat_with_rag(
                    model=req.model,
                    messages=messages,
                    collection_name=req.rag_collection,
                    top_k=req.rag_top_k,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    stream=False,
                )
            else:
                result = await _engine.chat(
                    model=req.model,
                    messages=messages,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                )
            return {"content": result.content, "model": result.model, "done": result.done}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=CompareResponseModel)
async def compare(req: CompareRequest):
    """Compare responses from multiple models."""
    messages = [ChatMessage(role=m["role"], content=m["content"]) for m in req.messages]
    try:
        result = await _engine.compare(
            models=req.models,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return CompareResponseModel(
            responses={
                model: {
                    "content": resp.content,
                    "model": resp.model,
                    "eval_count": resp.eval_count,
                    "total_duration_ns": resp.total_duration_ns,
                }
                for model, resp in result.responses.items()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
