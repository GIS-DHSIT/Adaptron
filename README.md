# Adaptron

**End-to-end LLM Fine-tuning Framework**

<!-- Badges placeholder -->
<!-- ![PyPI](https://img.shields.io/pypi/v/adaptron) -->
<!-- ![Python](https://img.shields.io/pypi/pyversions/adaptron) -->
<!-- ![License](https://img.shields.io/github/license/GIS-DHSIT/adaptron) -->

---

## Overview

Adaptron is a plugin-based framework that takes you from raw documents to a deployed, fine-tuned language model. It orchestrates six pipeline stages -- **Ingest, Understand, Synthesize, Train, Evaluate, Deploy** -- and exposes the entire workflow through a Python API, a CLI, a FastAPI backend, and a Next.js web UI.

## Features

- **Multi-format ingestion** -- PDF, DOCX, CSV, and SQL data sources
- **Semantic understanding** -- chunking, entity extraction, quality scoring, schema inference
- **Instruction synthesis** -- template-based training data generation
- **Multiple training strategies** -- QLoRA (Unsloth+PEFT), Full Fine-Tuning, Continual Pre-Training, Distillation, DPO alignment
- **Domain evaluation** -- automated scoring of fine-tuned models
- **One-click deployment** -- Ollama, GGUF export, HuggingFace Hub push
- **Training Strategy Wizard** -- answers seven questions, picks the best training mode and base model automatically
- **Playground** -- chat with deployed models, compare outputs side-by-side, toggle RAG augmentation
- **Plugin system** -- register custom ingesters, trainers, deployers, or any stage component
- **Event-driven pipeline** -- real-time progress via EventBus and WebSocket

## Quick Start

```bash
# Install with all optional dependencies
pip install -e ".[all]"

# Initialize a project
adaptron init --project-dir my-project
cd my-project

# Edit adaptron.yaml, then run the pipeline
adaptron run
```

## Installation

Requires **Python 3.11+**.

```bash
# Core only (config, CLI, pipeline orchestrator)
pip install -e .

# With specific extras
pip install -e ".[train]"       # torch, transformers, PEFT, TRL, bitsandbytes
pip install -e ".[ingest]"      # pypdf, python-docx, pandas, sqlalchemy
pip install -e ".[understand]"  # spacy, sentence-transformers
pip install -e ".[rag]"         # chromadb, sentence-transformers
pip install -e ".[api]"         # fastapi, uvicorn, websockets
pip install -e ".[deploy]"      # huggingface-hub

# Everything
pip install -e ".[all]"

# Development (pytest, ruff, coverage)
pip install -e ".[dev]"
```

## Usage

### Python API

```python
from adaptron.core.config import PipelineConfig, WizardAnswers

# Let the wizard pick the best strategy
answers = WizardAnswers(
    primary_goal="qa_docs",
    data_sources=["docs"],
    data_freshness="static",
    hardware="mid",
    timeline="medium",
    accuracy="professional",
    model_size="small",
)
config = PipelineConfig.from_wizard(answers)

print(config.base_model)       # e.g. Qwen/Qwen2.5-7B-Instruct
print(config.training_modes)   # e.g. ['qlora', 'rag']

# Or load from YAML
config = PipelineConfig.from_yaml("adaptron.yaml")
```

### CLI Commands

```bash
adaptron version              # Show version
adaptron init                 # Create adaptron.yaml with defaults
adaptron run                  # Execute the pipeline
adaptron wizard               # Interactive training strategy wizard
adaptron playground           # Chat with a finetuned model via Ollama
adaptron playground --rag     # Chat with RAG context augmentation
```

### Web UI

```bash
# Start the FastAPI backend
uvicorn adaptron.api.main:create_app --factory --reload

# In a separate terminal, start the Next.js frontend
cd web && npm install && npm run dev
```

Then open [http://localhost:3000](http://localhost:3000) to access the Wizard, Dashboard, and Playground.

## Architecture

```
                         adaptron.yaml
                              |
                              v
  +-------+  +------------+  +------------+  +-------+  +----------+  +--------+
  |Ingest | ->| Understand | ->| Synthesize | ->| Train | ->| Evaluate | ->| Deploy |
  +-------+  +------------+  +------------+  +-------+  +----------+  +--------+
   PDF,DOCX   Chunker,        Instruction     QLoRA,     Domain        Ollama,
   CSV,SQL    Entities,        templates      FullFT,    scoring       GGUF,
              Quality,                        CPT,DPO,                 HF Hub
              Schema                          Distill

  All stages are plugins registered in the global PluginRegistry.
  The PipelineOrchestrator runs them sequentially, emitting events
  via EventBus that the WebSocket API streams to the frontend.
```

## Plugin System

Every pipeline component is a plugin. Register your own with the `@register_plugin` decorator:

```python
from adaptron.core.registry import register_plugin
from adaptron.ingest.base import BaseIngester, IngesterResult

@register_plugin("ingest", "my_custom")
class MyCustomIngester(BaseIngester):
    async def ingest(self, source: str, **kwargs) -> IngesterResult:
        # Your custom ingestion logic
        ...
```

Retrieve plugins at runtime:

```python
from adaptron.core.registry import global_registry

ingester_cls = global_registry.get("ingest", "my_custom")
```

## Pipeline Stages

| Stage | Module | Plugins | Description |
|-------|--------|---------|-------------|
| **Ingest** | `adaptron.ingest` | `pdf`, `docx`, `csv`, `sql` | Extract text and metadata from data sources |
| **Understand** | `adaptron.understand` | `chunker`, `entities`, `quality`, `schema` | Semantic chunking, entity extraction, quality scoring, schema inference |
| **Synthesize** | `adaptron.synthesize` | `instruction` | Generate instruction-response training pairs from chunks |
| **Train** | `adaptron.train` | `qlora`, `full_ft`, `cpt`, `distill`, `alignment` (DPO) | Fine-tune or align the base model |
| **Evaluate** | `adaptron.evaluate` | `domain` | Score model outputs against domain-specific criteria |
| **Deploy** | `adaptron.deploy` | `ollama`, `gguf`, `huggingface` | Export and deploy the fine-tuned model |

## Playground

The playground lets you interact with deployed models:

- **Chat mode** -- streaming conversation with any Ollama-hosted model
- **RAG toggle** -- augment prompts with relevant context from ChromaDB
- **Comparison mode** -- send the same prompt to two models side-by-side (web UI)
- **CLI access** -- `adaptron playground --model adaptron-mymodel --rag`

## Configuration

Adaptron uses a YAML configuration file (`adaptron.yaml`):

```yaml
# Wizard answers -- drive automatic strategy selection
wizard:
  primary_goal: qa_docs          # qa_docs | erp_edw | report_gen | specialist
  data_sources:
    - docs                       # docs | erp | edw
  data_freshness: static         # static | monthly | daily | realtime
  hardware: mid                  # low | mid | high | cloud
  timeline: medium               # fast | medium | long | unlimited
  accuracy: professional         # professional | enterprise | mission
  model_size: small              # tiny | small | medium | large

# Manual overrides
overrides:
  epochs: 3
  learning_rate: 0.0002
  batch_size: 4
  lora_rank: 64
  max_seq_length: 2048
  quantization: Q4_K_M

data:
  input_dir: ./data
  output_dir: ./output

deploy:
  targets:
    - gguf
    - ollama
```

## Development

```bash
# Clone and install in dev mode
git clone <repo-url> && cd Adaptron
pip install -e ".[all,dev]"

# Run the test suite
pytest --tb=short -q

# Lint
ruff check adaptron/ tests/
```

## License

MIT License. See [LICENSE](LICENSE) for details.
