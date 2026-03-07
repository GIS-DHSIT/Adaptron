# Playground Feature Design

**Date:** 2026-03-07
**Status:** Approved

## Overview

A playground for users to test their fine-tuned models with custom prompts. Supports chat, side-by-side comparison (finetuned vs base model), and RAG context toggle. Available as a web UI page, CLI command, and Python API.

## Architecture

```
Frontend (/playground)  -->  FastAPI (/api/playground/*)  -->  Ollama API (:11434)
                                      |
                                      v (when RAG enabled)
                                   ChromaDB
```

## Components

### 1. PlaygroundEngine (adaptron/playground/engine.py)

Core Python class for inference:
- `chat(model, messages, stream, temperature, max_tokens)` - single model chat via Ollama HTTP
- `chat_with_rag(model, messages, collection, top_k)` - retrieve chunks, inject into system prompt, then chat
- `compare(models, messages)` - parallel inference on multiple models
- `list_models()` - list available Ollama models (filtered to adaptron-* ones)

Uses `httpx` for async HTTP calls to Ollama API at `http://localhost:11434`.

### 2. FastAPI Routes (adaptron/api/routes/playground.py)

- `GET /api/playground/models` - list available models
- `POST /api/playground/chat` - chat with streaming SSE response
- `POST /api/playground/compare` - compare two models side-by-side

### 3. CLI Command (adaptron/cli/main.py)

- `adaptron playground [--model NAME]` - interactive terminal chat with the finetuned model

### 4. Web UI (web/app/playground/page.tsx)

Chat interface with:
- Message history (user/assistant bubbles)
- Model selector dropdown
- RAG toggle switch
- Temperature and max tokens sliders
- Comparison mode toggle (splits view into two panels)
- Streaming response display

## Data Flow

1. User sends prompt from UI/CLI
2. Backend checks RAG toggle -> if enabled, retrieves top-K chunks from ChromaDB
3. RAG chunks are prepended to system prompt as context
4. Backend calls `POST http://localhost:11434/api/chat` with `stream: true`
5. Backend streams response tokens back via SSE (web) or stdout (CLI)

## Comparison Mode

- User enters one prompt
- Backend sends it to both the finetuned model and the base model in parallel
- Frontend displays both responses side-by-side with timing info

## Technology

- httpx (async HTTP client for Ollama API calls)
- SSE via FastAPI StreamingResponse
- No extra ML dependencies
