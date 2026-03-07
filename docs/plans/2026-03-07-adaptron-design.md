# Adaptron Design Document

**Date:** 2026-03-07
**Status:** Approved

## Overview

Adaptron is an end-to-end LLM fine-tuning framework that takes user-provided data and produces a custom fine-tuned AI model ready for deployment. It consists of a Python core library with CLI, a FastAPI backend, and a Next.js web UI featuring a Training Strategy Wizard (ported from the LocalMind Studio wizard).

## Requirements

### Functional
- Support all major fine-tuning approaches: QLoRA, Full Fine-Tuning, Continued Pre-Training, Knowledge Distillation, RLHF/DPO alignment, and RAG-augmented SLM
- End-to-end pipeline: data ingestion, intelligent context understanding, synthetic dataset generation, training, evaluation, deployment
- Training Strategy Wizard that analyzes user constraints and recommends optimal training configuration
- Deploy trained models to Ollama (local hosting), vLLM (cloud API), and HuggingFace Hub
- Every component must be plug-and-play via a registry-based plugin system

### Non-Functional
- Robust and extensible architecture ready for future enhancements
- Async pipeline execution with real-time progress reporting
- Checkpoint/resume support for long-running training jobs
- Usable as Python library, CLI tool, or via web UI

## Architecture

### Approach: Modular Pipeline with Task Queue

Discrete, composable pipeline stages orchestrated by an async task system. Each stage is an independent module with a defined interface.

```
+-------------------------------------------------------------+
|                    ADAPTRON SYSTEM                           |
|                                                             |
|  +-------------+    +----------------------------------+    |
|  |  Web UI     |    |  FastAPI Backend                 |    |
|  |  (Next.js)  |<-->|  - REST API                     |    |
|  |  - Wizard   |    |  - WebSocket (progress)         |    |
|  |  - Dashboard|    |  - Pipeline orchestrator        |    |
|  |  - Monitor  |    +----------------+-----------------+    |
|  +-------------+                     |                      |
|                                      v                      |
|  +------------------------------------------------------+  |
|  |  ADAPTRON CORE (Python Library + CLI)                 |  |
|  |                                                       |  |
|  |  [Ingest] -> [Understand] -> [Synthesize] -> [Train]  |  |
|  |                                                |      |  |
|  |                              [Deploy] <- [Evaluate]   |  |
|  +------------------------------------------------------+  |
|                                                             |
|  +----------+  +----------+  +----------+                   |
|  | ChromaDB |  |  SQLite  |  |  Redis   |                   |
|  | (vectors)|  | (metadata)|  | (tasks)  |                   |
|  +----------+  +----------+  +----------+                   |
+-------------------------------------------------------------+
```

**Key decisions:**
- Adaptron Core is a standalone Python package -- works without the web UI via CLI or Python API
- FastAPI Backend is a thin orchestration layer that calls core modules and reports progress via WebSocket
- SQLite for project/run metadata (zero-config), ChromaDB for RAG vectors, Redis optional (in-process queue for dev)
- The wizard config maps directly to a PipelineConfig dataclass that drives the entire pipeline

## Plugin Architecture

Every pipeline stage defines an abstract interface. Implementations register via decorators.

```python
# Every stage has a base interface
class BaseIngester(ABC):
    @abstractmethod
    def ingest(self, source: DataSource) -> Dataset: ...

class BaseTrainer(ABC):
    @abstractmethod
    def train(self, config: TrainConfig, dataset: Dataset) -> TrainResult: ...

# Implementations register via decorator
@register_plugin("ingester", "pdf")
class PDFIngester(BaseIngester): ...

@register_plugin("trainer", "qlora")
class QLoRATrainer(BaseTrainer): ...

# Runtime resolution
trainer = PluginRegistry.get("trainer", config.training_mode)
```

### 6 Core Pipeline Stages

| Stage | Interface | Built-in Plugins | Purpose |
|-------|-----------|-----------------|---------|
| **Ingest** | `BaseIngester` | PDF, DOCX, SQL, ERP connector | Extract raw data from sources |
| **Understand** | `BaseAnalyzer` | Entity extractor, Schema inferrer, Quality scorer | Algorithmic context understanding |
| **Synthesize** | `BaseSynthesizer` | Instruction gen, QA gen, DPO gen | Create training datasets |
| **Train** | `BaseTrainer` | QLoRA (Unsloth), Full FT (HF), CPT, Distill, DPO/RLHF | Execute training |
| **Evaluate** | `BaseEvaluator` | Benchmark suite, Domain accuracy, Perplexity | Assess model quality |
| **Deploy** | `BaseDeployer` | GGUF export, vLLM, HuggingFace Hub, Ollama | Package and ship |

### Extension Points
- Custom ingesters for new data source connectors
- Custom trainers for new training algorithms
- Custom evaluators for domain-specific metrics
- Custom deployers for new deployment targets
- Pipeline hooks: `on_stage_start`, `on_stage_complete`, `on_error`

## Data Flow

```
User Data (PDFs, DBs, ERPs)
        |
        v
--- INGEST ---
  PDF -> extract text + tables
  DB  -> query schema + sample rows
  ERP -> connect via adapter, pull relevant tables
  Output: RawDocument[] (text, metadata, source_ref)
        |
        v
--- UNDERSTAND ---
  Smart Chunking: semantic-aware splitting (not naive)
  Entity Extraction: NER + domain concept mapping
  Schema Inference: table -> NL descriptions, FK mapping
  Quality Scoring: dedup, noise detection, coverage
  Output: AnalyzedCorpus (chunks, entities, quality)
        |
        v
--- SYNTHESIZE ---
  Based on training mode + goal:
  - QLoRA/Full FT -> instruction-response pairs
  - CPT -> cleaned domain corpus
  - DPO -> preference pairs (chosen/rejected)
  - Distill -> teacher-student generation
  - RAG -> chunk embeddings + metadata
  Output: TrainingDataset (HF Dataset format)
        |
        v
--- TRAIN ---
  Download base model (auto-selected or user choice)
  Apply training mode:
    QLoRA -> Unsloth 4-bit, LoRA adapters
    Full FT -> HF Trainer, all params
    CPT -> causal LM continued training
    Distill -> teacher forward pass -> student loss
    DPO -> TRL DPOTrainer
  Output: TrainedModel (adapter or merged weights)
  Events: loss, lr, epoch progress -> WebSocket
        |
        v
--- EVALUATE ---
  Compare trained vs. base on:
    - Domain accuracy (hold-out QA set)
    - Perplexity on domain corpus
    - Standard benchmarks (optional)
  Output: EvalReport (metrics, comparison, pass/fail)
        |
        v
--- DEPLOY ---
  Based on target:
    GGUF -> llama.cpp quantize -> Ollama modelfile -> ollama create -> serve
    vLLM -> containerized API endpoint
    HF Hub -> push model + model card
  Output: DeploymentArtifact (path, URL, or model ID)
```

## Pipeline Configuration

The wizard's 7 answers map to a PipelineConfig:

```python
@dataclass
class PipelineConfig:
    # From wizard
    primary_goal: str        # qa_docs, erp_edw, report_gen, specialist
    data_sources: list[str]  # docs, erp, edw, db
    data_freshness: str      # static, monthly, daily, realtime
    hardware: str            # low, mid, high, cloud
    timeline: str            # fast, medium, long, unlimited
    accuracy: str            # exploratory, professional, enterprise, mission
    model_size: str          # tiny, small, medium, large

    # Derived by scoring engine
    training_modes: list[str]    # e.g., ["qlora", "rag"]
    base_model: str              # e.g., "Qwen/Qwen2.5-7B"
    deploy_targets: list[str]    # e.g., ["gguf", "ollama"]

    # User overrides (optional)
    custom_base_model: str | None = None
    lora_rank: int = 64
    epochs: int = 3
    learning_rate: float = 2e-4
```

## Execution Model

```python
# CLI usage
adaptron run --config pipeline.yaml

# Python API usage
from adaptron import Pipeline
pipeline = Pipeline.from_config("pipeline.yaml")
result = await pipeline.execute()

# Web API usage
POST /api/pipelines/start  -> returns pipeline_id
WS   /api/pipelines/{id}/progress -> real-time events
```

## Ollama Integration (First-Class)

The deploy stage provides full Ollama integration:
1. Quantize trained model to GGUF (Q4_K_M default, configurable)
2. Generate an Ollama Modelfile with system prompt + parameters
3. Register with local Ollama via `ollama create adaptron-{project}`
4. Optionally start serving immediately via `ollama serve`

## Project Structure

```
adaptron/
  core/
    config.py          # PipelineConfig, TrainConfig dataclasses
    registry.py        # PluginRegistry
    pipeline.py        # PipelineOrchestrator
    events.py          # Event bus for progress/hooks
  ingest/
    base.py            # BaseIngester interface
    pdf.py, docx.py, sql.py, erp.py
  understand/
    base.py            # BaseAnalyzer interface
    chunker.py         # Smart chunking
    entities.py        # Entity extraction
    schema.py          # DB schema inference
    quality.py         # Data quality scoring
  synthesize/
    base.py            # BaseSynthesizer interface
    instruction.py     # Instruction pair generation
    qa.py              # QA pair generation
    dpo.py             # DPO preference pair generation
  train/
    base.py            # BaseTrainer interface
    qlora.py           # QLoRA via Unsloth
    full_ft.py         # Full fine-tuning via HF
    cpt.py             # Continued pre-training
    distill.py         # Knowledge distillation
    alignment.py       # RLHF/DPO via TRL
  evaluate/
    base.py            # BaseEvaluator interface
    benchmark.py       # Standard benchmarks
    domain.py          # Domain-specific eval
  deploy/
    base.py            # BaseDeployer interface
    gguf.py            # GGUF export
    ollama.py          # Ollama integration (create + serve)
    vllm.py            # vLLM deployment
    huggingface.py     # HF Hub push
  rag/
    indexer.py         # ChromaDB indexing
    retriever.py       # RAG retrieval
  api/                 # FastAPI backend
    main.py
    routes/
    websocket.py       # Real-time progress
  cli/                 # CLI commands
    main.py            # Typer CLI
  web/                 # Next.js frontend
    (wizard + dashboard)
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Core framework | Python 3.11+, asyncio |
| Training | transformers, PEFT, TRL, Unsloth, datasets |
| Data processing | LangChain (document loaders), spaCy (NER), pandas |
| Synthetic data | LLM-based generation (local model or API) |
| RAG | ChromaDB, sentence-transformers |
| API | FastAPI, uvicorn, WebSockets |
| Task queue | In-process asyncio (dev), Celery+Redis (prod) |
| Metadata DB | SQLite via SQLAlchemy |
| CLI | Typer |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Model export | llama.cpp (GGUF), Ollama modelfile |
| Deployment | Ollama (local hosting), vLLM (cloud), HF Hub |
| Testing | pytest, pytest-asyncio |
| Package | pyproject.toml, uv/pip |

## Error Handling

- Each pipeline stage saves checkpoints -- if training fails at epoch 5, resume from epoch 5
- Stage outputs are cached -- re-running a pipeline skips completed stages
- Clear error messages with actionable suggestions (e.g., "OOM: reduce batch size or switch to QLoRA")
- WebSocket emits error events with stage context
