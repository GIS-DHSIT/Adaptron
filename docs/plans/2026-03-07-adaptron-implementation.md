# Adaptron Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an end-to-end LLM fine-tuning framework with plugin architecture, 6 pipeline stages, CLI, FastAPI backend, and Next.js frontend.

**Architecture:** Modular pipeline with registry-based plugin system. Each stage (Ingest, Understand, Synthesize, Train, Evaluate, Deploy) has an abstract interface with swappable implementations. Async execution with event-driven progress reporting.

**Tech Stack:** Python 3.11+, HuggingFace (transformers/PEFT/TRL), Unsloth, FastAPI, Next.js 14, ChromaDB, SQLite, Typer CLI

---

## Phase 1: Project Scaffolding & Core Infrastructure

### Task 1: Project setup and package configuration

**Files:**
- Create: `pyproject.toml`
- Create: `adaptron/__init__.py`
- Create: `adaptron/core/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/core/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "adaptron"
version = "0.1.0"
description = "End-to-end LLM Fine-tuning Framework"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "typer>=0.12",
    "rich>=13.0",
]

[project.optional-dependencies]
train = [
    "torch>=2.1",
    "transformers>=4.40",
    "peft>=0.10",
    "trl>=0.8",
    "datasets>=2.18",
    "accelerate>=0.28",
    "bitsandbytes>=0.43",
]
ingest = [
    "langchain-community>=0.2",
    "pypdf>=4.0",
    "python-docx>=1.1",
    "pandas>=2.2",
    "sqlalchemy>=2.0",
    "openpyxl>=3.1",
]
understand = [
    "spacy>=3.7",
    "sentence-transformers>=2.6",
]
rag = [
    "chromadb>=0.5",
    "sentence-transformers>=2.6",
]
api = [
    "fastapi>=0.110",
    "uvicorn>=0.29",
    "websockets>=12.0",
]
deploy = [
    "huggingface-hub>=0.22",
]
all = ["adaptron[train,ingest,understand,rag,api,deploy]"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "ruff>=0.3",
]

[project.scripts]
adaptron = "adaptron.cli.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py311"
line-length = 100
```

**Step 2: Create package init files**

`adaptron/__init__.py`:
```python
"""Adaptron - End-to-end LLM Fine-tuning Framework."""
__version__ = "0.1.0"
```

`adaptron/core/__init__.py`:
```python
"""Core infrastructure: config, registry, pipeline, events."""
```

`tests/__init__.py` and `tests/core/__init__.py`: empty files.

**Step 3: Verify setup**

Run: `pip install -e ".[dev]"` then `python -c "import adaptron; print(adaptron.__version__)"`
Expected: `0.1.0`

**Step 4: Commit**

```bash
git add pyproject.toml adaptron/ tests/
git commit -m "feat: project scaffolding with pyproject.toml and package structure"
```

---

### Task 2: Plugin registry system

**Files:**
- Create: `adaptron/core/registry.py`
- Create: `tests/core/test_registry.py`

**Step 1: Write failing tests**

```python
# tests/core/test_registry.py
from adaptron.core.registry import PluginRegistry, register_plugin


class DummyBase:
    pass


def test_register_and_get_plugin():
    registry = PluginRegistry()

    @registry.register("trainer", "qlora")
    class QLoRATrainer(DummyBase):
        name = "qlora"

    plugin = registry.get("trainer", "qlora")
    assert plugin is QLoRATrainer


def test_get_missing_plugin_raises():
    registry = PluginRegistry()
    try:
        registry.get("trainer", "nonexistent")
        assert False, "Should have raised"
    except KeyError:
        pass


def test_list_plugins():
    registry = PluginRegistry()

    @registry.register("trainer", "qlora")
    class A(DummyBase):
        pass

    @registry.register("trainer", "full_ft")
    class B(DummyBase):
        pass

    plugins = registry.list_plugins("trainer")
    assert set(plugins) == {"qlora", "full_ft"}


def test_list_plugins_empty_category():
    registry = PluginRegistry()
    assert registry.list_plugins("unknown") == []


def test_register_duplicate_warns(caplog):
    import logging
    registry = PluginRegistry()

    @registry.register("trainer", "qlora")
    class A(DummyBase):
        pass

    with caplog.at_level(logging.WARNING):
        @registry.register("trainer", "qlora")
        class B(DummyBase):
            pass

    assert "Overwriting" in caplog.text
    assert registry.get("trainer", "qlora") is B
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/core/test_registry.py -v`
Expected: ImportError

**Step 3: Implement registry**

```python
# adaptron/core/registry.py
"""Plugin registry for extensible pipeline components."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for discovering and resolving pipeline plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, dict[str, type]] = {}

    def register(self, category: str, name: str):
        """Decorator to register a plugin class under category/name."""
        def decorator(cls: type) -> type:
            if category not in self._plugins:
                self._plugins[category] = {}
            if name in self._plugins[category]:
                logger.warning(
                    "Overwriting plugin %s/%s: %s -> %s",
                    category, name,
                    self._plugins[category][name].__name__, cls.__name__,
                )
            self._plugins[category][name] = cls
            return cls
        return decorator

    def get(self, category: str, name: str) -> type:
        """Resolve a plugin by category and name. Raises KeyError if not found."""
        try:
            return self._plugins[category][name]
        except KeyError:
            available = self.list_plugins(category)
            raise KeyError(
                f"Plugin '{name}' not found in category '{category}'. "
                f"Available: {available}"
            )

    def list_plugins(self, category: str) -> list[str]:
        """List all registered plugin names in a category."""
        return list(self._plugins.get(category, {}).keys())


# Global registry instance
global_registry = PluginRegistry()


def register_plugin(category: str, name: str):
    """Register a plugin in the global registry."""
    return global_registry.register(category, name)
```

**Step 4: Run tests**

Run: `pytest tests/core/test_registry.py -v`
Expected: All 5 pass

**Step 5: Commit**

```bash
git add adaptron/core/registry.py tests/core/test_registry.py
git commit -m "feat: plugin registry system with decorator-based registration"
```

---

### Task 3: Event bus for progress reporting

**Files:**
- Create: `adaptron/core/events.py`
- Create: `tests/core/test_events.py`

**Step 1: Write failing tests**

```python
# tests/core/test_events.py
from adaptron.core.events import EventBus, Event


def test_sync_listener():
    bus = EventBus()
    received = []
    bus.on("stage_start", lambda e: received.append(e))
    bus.emit("stage_start", Event(type="stage_start", data={"stage": "ingest"}))
    assert len(received) == 1
    assert received[0].data["stage"] == "ingest"


def test_multiple_listeners():
    bus = EventBus()
    count = {"a": 0, "b": 0}
    bus.on("progress", lambda e: count.__setitem__("a", count["a"] + 1))
    bus.on("progress", lambda e: count.__setitem__("b", count["b"] + 1))
    bus.emit("progress", Event(type="progress", data={}))
    assert count["a"] == 1
    assert count["b"] == 1


def test_no_listeners_no_error():
    bus = EventBus()
    bus.emit("unknown", Event(type="unknown", data={}))


def test_wildcard_listener():
    bus = EventBus()
    received = []
    bus.on("*", lambda e: received.append(e.type))
    bus.emit("stage_start", Event(type="stage_start", data={}))
    bus.emit("stage_end", Event(type="stage_end", data={}))
    assert received == ["stage_start", "stage_end"]
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/core/test_events.py -v`

**Step 3: Implement event bus**

```python
# adaptron/core/events.py
"""Event bus for pipeline progress and hook notifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import time


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Event], None]]] = {}

    def on(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event_type: str, event: Event) -> None:
        for cb in self._listeners.get(event_type, []):
            cb(event)
        if event_type != "*":
            for cb in self._listeners.get("*", []):
                cb(event)

    def off(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb is not callback
            ]
```

**Step 4: Run tests**

Run: `pytest tests/core/test_events.py -v`
Expected: All 4 pass

**Step 5: Commit**

```bash
git add adaptron/core/events.py tests/core/test_events.py
git commit -m "feat: event bus for pipeline progress and hook notifications"
```

---

### Task 4: Pipeline configuration dataclasses

**Files:**
- Create: `adaptron/core/config.py`
- Create: `tests/core/test_config.py`

**Step 1: Write failing tests**

```python
# tests/core/test_config.py
import yaml
import tempfile
from pathlib import Path
from adaptron.core.config import PipelineConfig, WizardAnswers


def test_wizard_answers_defaults():
    wa = WizardAnswers(
        primary_goal="qa_docs", data_sources=["docs"],
        data_freshness="static", hardware="mid",
        timeline="medium", accuracy="professional", model_size="small",
    )
    assert wa.primary_goal == "qa_docs"


def test_pipeline_config_from_wizard():
    wa = WizardAnswers(
        primary_goal="qa_docs", data_sources=["docs"],
        data_freshness="static", hardware="mid",
        timeline="medium", accuracy="professional", model_size="small",
    )
    config = PipelineConfig.from_wizard(wa)
    assert "qlora" in config.training_modes
    assert config.base_model is not None
    assert config.epochs == 3


def test_pipeline_config_from_yaml():
    data = {
        "wizard": {
            "primary_goal": "specialist", "data_sources": ["docs", "db"],
            "data_freshness": "static", "hardware": "high",
            "timeline": "long", "accuracy": "enterprise", "model_size": "medium",
        },
        "overrides": {"epochs": 5, "learning_rate": 1e-4},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        f.flush()
        config = PipelineConfig.from_yaml(Path(f.name))
    assert config.epochs == 5
    assert config.learning_rate == 1e-4


def test_pipeline_config_to_yaml(tmp_path):
    wa = WizardAnswers(
        primary_goal="qa_docs", data_sources=["docs"],
        data_freshness="static", hardware="mid",
        timeline="medium", accuracy="professional", model_size="small",
    )
    config = PipelineConfig.from_wizard(wa)
    path = tmp_path / "config.yaml"
    config.to_yaml(path)
    assert path.exists()
    loaded = PipelineConfig.from_yaml(path)
    assert loaded.training_modes == config.training_modes
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/core/test_config.py -v`

**Step 3: Implement config**

```python
# adaptron/core/config.py
"""Pipeline configuration and wizard-to-config translation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WizardAnswers:
    primary_goal: str
    data_sources: list[str]
    data_freshness: str
    hardware: str
    timeline: str
    accuracy: str
    model_size: str


@dataclass
class PipelineConfig:
    primary_goal: str = ""
    data_sources: list[str] = field(default_factory=list)
    data_freshness: str = ""
    hardware: str = ""
    timeline: str = ""
    accuracy: str = ""
    model_size: str = ""
    training_modes: list[str] = field(default_factory=list)
    base_model: str = ""
    deploy_targets: list[str] = field(default_factory=lambda: ["gguf", "ollama"])
    custom_base_model: str | None = None
    lora_rank: int = 64
    epochs: int = 3
    learning_rate: float = 2e-4
    batch_size: int = 4
    max_seq_length: int = 2048
    quantization: str = "Q4_K_M"

    @classmethod
    def from_wizard(cls, answers: WizardAnswers) -> PipelineConfig:
        config = cls(
            primary_goal=answers.primary_goal,
            data_sources=answers.data_sources,
            data_freshness=answers.data_freshness,
            hardware=answers.hardware,
            timeline=answers.timeline,
            accuracy=answers.accuracy,
            model_size=answers.model_size,
        )
        config.training_modes = _compute_training_modes(answers)
        config.base_model = _select_base_model(answers)
        return config

    @classmethod
    def from_yaml(cls, path: Path) -> PipelineConfig:
        with open(path) as f:
            data = yaml.safe_load(f)
        wizard_data = data.get("wizard", {})
        overrides = data.get("overrides", {})
        if wizard_data:
            answers = WizardAnswers(**wizard_data)
            config = cls.from_wizard(answers)
        else:
            config = cls()
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

    def to_yaml(self, path: Path) -> None:
        data = {
            "wizard": {
                "primary_goal": self.primary_goal,
                "data_sources": self.data_sources,
                "data_freshness": self.data_freshness,
                "hardware": self.hardware,
                "timeline": self.timeline,
                "accuracy": self.accuracy,
                "model_size": self.model_size,
            },
            "overrides": {
                "epochs": self.epochs,
                "learning_rate": self.learning_rate,
                "batch_size": self.batch_size,
                "lora_rank": self.lora_rank,
                "max_seq_length": self.max_seq_length,
                "quantization": self.quantization,
            },
        }
        if self.custom_base_model:
            data["overrides"]["custom_base_model"] = self.custom_base_model
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _compute_training_modes(answers: WizardAnswers) -> list[str]:
    scores: dict[str, int] = {"qlora": 0, "cpt": 0, "distill": 0, "rag": 0}
    goal = answers.primary_goal
    if goal == "qa_docs":
        scores["qlora"] += 3; scores["rag"] += 2
    elif goal == "erp_edw":
        scores["rag"] += 4; scores["qlora"] += 1
    elif goal == "report_gen":
        scores["qlora"] += 4; scores["distill"] += 2
    elif goal == "specialist":
        scores["cpt"] += 4; scores["qlora"] += 2
    if "erp" in answers.data_sources or "edw" in answers.data_sources:
        scores["rag"] += 3
    if answers.data_sources == ["docs"]:
        scores["qlora"] += 2
    if len(answers.data_sources) >= 3:
        scores["rag"] += 2
    if answers.data_freshness == "static":
        scores["qlora"] += 3; scores["cpt"] += 2
    elif answers.data_freshness == "monthly":
        scores["qlora"] += 1; scores["rag"] += 2
    elif answers.data_freshness in ("daily", "realtime"):
        scores["rag"] += 5; scores["qlora"] -= 2
    if answers.hardware == "low":
        scores["cpt"] -= 5; scores["distill"] += 2
    elif answers.hardware in ("high", "cloud"):
        scores["cpt"] += 3
    if answers.timeline == "fast":
        scores["cpt"] -= 5; scores["distill"] -= 2
    elif answers.timeline in ("long", "unlimited"):
        scores["cpt"] += 2
    if answers.accuracy == "enterprise":
        scores["qlora"] += 2; scores["rag"] += 3
    elif answers.accuracy == "mission":
        scores["rag"] += 5; scores["cpt"] += 2
    if answers.model_size == "tiny":
        scores["distill"] += 4; scores["cpt"] -= 3
    elif answers.model_size == "small":
        scores["qlora"] += 2
    elif answers.model_size == "large":
        scores["cpt"] += 2
    modes = [k for k, v in sorted(scores.items(), key=lambda x: -x[1]) if v > 0]
    return modes if modes else ["qlora"]


def _select_base_model(answers: WizardAnswers) -> str:
    if answers.hardware == "low" and answers.model_size in ("medium", "large"):
        return "microsoft/phi-3.5-mini-instruct"
    models = {
        "tiny": "microsoft/phi-3.5-mini-instruct",
        "small": "Qwen/Qwen2.5-7B-Instruct",
        "medium": "Qwen/Qwen2.5-14B-Instruct",
        "large": "Qwen/Qwen2.5-32B-Instruct",
    }
    return models.get(answers.model_size, "Qwen/Qwen2.5-7B-Instruct")
```

**Step 4: Run tests**

Run: `pytest tests/core/test_config.py -v`
Expected: All 4 pass

**Step 5: Commit**

```bash
git add adaptron/core/config.py tests/core/test_config.py
git commit -m "feat: pipeline config with wizard scoring engine and YAML serialization"
```

---

### Task 5: Pipeline orchestrator

**Files:**
- Create: `adaptron/core/pipeline.py`
- Create: `tests/core/test_pipeline.py`

**Step 1: Write failing tests**

```python
# tests/core/test_pipeline.py
import pytest
from adaptron.core.pipeline import PipelineOrchestrator, StageResult, StageStatus
from adaptron.core.events import EventBus


class FakeStage:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.executed = False

    async def run(self, context: dict) -> StageResult:
        self.executed = True
        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")
        context[self.name] = "done"
        return StageResult(status=StageStatus.COMPLETED, output={"result": "ok"})


@pytest.mark.asyncio
async def test_pipeline_runs_stages_in_order():
    bus = EventBus()
    pipeline = PipelineOrchestrator(bus=bus)
    s1 = FakeStage("ingest")
    s2 = FakeStage("understand")
    pipeline.add_stage("ingest", s1)
    pipeline.add_stage("understand", s2)
    result = await pipeline.execute({})
    assert s1.executed
    assert s2.executed
    assert result.status == StageStatus.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_stops_on_failure():
    bus = EventBus()
    pipeline = PipelineOrchestrator(bus=bus)
    s1 = FakeStage("ingest", should_fail=True)
    s2 = FakeStage("understand")
    pipeline.add_stage("ingest", s1)
    pipeline.add_stage("understand", s2)
    result = await pipeline.execute({})
    assert s1.executed
    assert not s2.executed
    assert result.status == StageStatus.FAILED


@pytest.mark.asyncio
async def test_pipeline_emits_events():
    bus = EventBus()
    events = []
    bus.on("*", lambda e: events.append(e.type))
    pipeline = PipelineOrchestrator(bus=bus)
    pipeline.add_stage("ingest", FakeStage("ingest"))
    await pipeline.execute({})
    assert "stage_start" in events
    assert "stage_complete" in events
    assert "pipeline_complete" in events
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/core/test_pipeline.py -v`

**Step 3: Implement pipeline orchestrator**

```python
# adaptron/core/pipeline.py
"""Pipeline orchestrator that runs stages sequentially with event reporting."""

from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from adaptron.core.events import Event, EventBus

logger = logging.getLogger(__name__)


class StageStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    status: StageStatus
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class PipelineResult:
    status: StageStatus
    stage_results: dict[str, StageResult] = field(default_factory=dict)
    total_duration: float = 0.0


class PipelineOrchestrator:
    def __init__(self, bus: EventBus | None = None) -> None:
        self._stages: list[tuple[str, Any]] = []
        self._bus = bus or EventBus()

    def add_stage(self, name: str, stage: Any) -> None:
        self._stages.append((name, stage))

    async def execute(self, context: dict | None = None) -> PipelineResult:
        context = context if context is not None else {}
        result = PipelineResult(status=StageStatus.RUNNING)
        start = time.time()

        self._bus.emit("pipeline_start", Event(
            type="pipeline_start",
            data={"stages": [name for name, _ in self._stages]},
        ))

        for name, stage in self._stages:
            self._bus.emit("stage_start", Event(type="stage_start", data={"stage": name}))
            stage_start = time.time()
            try:
                stage_result = await stage.run(context)
                stage_result.duration_seconds = time.time() - stage_start
                result.stage_results[name] = stage_result
                self._bus.emit("stage_complete", Event(
                    type="stage_complete",
                    data={"stage": name, "status": stage_result.status.value},
                ))
            except Exception as exc:
                stage_result = StageResult(
                    status=StageStatus.FAILED, error=str(exc),
                    duration_seconds=time.time() - stage_start,
                )
                result.stage_results[name] = stage_result
                self._bus.emit("stage_error", Event(
                    type="stage_error", data={"stage": name, "error": str(exc)},
                ))
                logger.error("Stage '%s' failed: %s", name, exc)
                result.status = StageStatus.FAILED
                result.total_duration = time.time() - start
                self._bus.emit("pipeline_complete", Event(
                    type="pipeline_complete", data={"status": "failed", "failed_stage": name},
                ))
                return result

        result.status = StageStatus.COMPLETED
        result.total_duration = time.time() - start
        self._bus.emit("pipeline_complete", Event(
            type="pipeline_complete", data={"status": "completed"},
        ))
        return result
```

**Step 4: Run tests**

Run: `pytest tests/core/test_pipeline.py -v`
Expected: All 3 pass

**Step 5: Commit**

```bash
git add adaptron/core/pipeline.py tests/core/test_pipeline.py
git commit -m "feat: pipeline orchestrator with sequential execution and event emission"
```

---

## Phase 2: Ingest Stage

### Task 6: Base ingester interface and data models

**Files:**
- Create: `adaptron/ingest/__init__.py`
- Create: `adaptron/ingest/base.py`
- Create: `adaptron/ingest/models.py`
- Create: `tests/ingest/__init__.py`
- Create: `tests/ingest/test_base.py`

**Step 1: Write failing tests**

```python
# tests/ingest/test_base.py
from adaptron.ingest.models import RawDocument, DataSource, SourceType
from adaptron.ingest.base import BaseIngester


def test_raw_document_creation():
    doc = RawDocument(content="Hello world", metadata={"source": "test.pdf", "page": 1}, source_ref="test.pdf")
    assert doc.content == "Hello world"
    assert doc.metadata["page"] == 1


def test_data_source_creation():
    src = DataSource(source_type=SourceType.PDF, path="/data/test.pdf")
    assert src.source_type == SourceType.PDF


def test_base_ingester_is_abstract():
    try:
        BaseIngester()
        assert False, "Should not instantiate abstract class"
    except TypeError:
        pass
```

**Step 2: Implement**

```python
# adaptron/ingest/models.py
from __future__ import annotations
import enum
from dataclasses import dataclass, field
from typing import Any


class SourceType(enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    HTML = "html"
    SQL = "sql"
    ERP = "erp"
    CSV = "csv"
    TEXT = "text"


@dataclass
class DataSource:
    source_type: SourceType
    path: str | None = None
    connection_string: str | None = None
    query: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class RawDocument:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source_ref: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
```

```python
# adaptron/ingest/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from adaptron.ingest.models import DataSource, RawDocument


class BaseIngester(ABC):
    @abstractmethod
    def ingest(self, source: DataSource) -> list[RawDocument]: ...

    @abstractmethod
    def supported_types(self) -> list[str]: ...
```

**Step 3: Run tests, commit**

---

### Task 7: PDF ingester

**Files:**
- Create: `adaptron/ingest/pdf.py`
- Create: `tests/ingest/test_pdf.py`

Implement `PDFIngester` using `pypdf` to extract text page-by-page. Register with `@register_plugin("ingester", "pdf")`.

---

### Task 8: SQL database ingester

**Files:**
- Create: `adaptron/ingest/sql.py`
- Create: `tests/ingest/test_sql.py`

Implement `SQLIngester` using `sqlalchemy` to extract schema + sample data from any SQL database. Register with `@register_plugin("ingester", "sql")`.

---

## Phase 3: Understand Stage

### Task 9: Smart chunker

**Files:**
- Create: `adaptron/understand/__init__.py`
- Create: `adaptron/understand/base.py`
- Create: `adaptron/understand/models.py`
- Create: `adaptron/understand/chunker.py`
- Create: `tests/understand/test_chunker.py`

Implement `SemanticChunker` with paragraph-aware and sentence-aware splitting. Register with `@register_plugin("analyzer", "chunker")`.

---

### Task 10: Entity extractor and quality scorer

**Files:**
- Create: `adaptron/understand/entities.py`
- Create: `adaptron/understand/quality.py`
- Create: `tests/understand/test_entities.py`
- Create: `tests/understand/test_quality.py`

Implement `RegexEntityExtractor` (emails, dates, money, URLs) and `QualityScorer` (duplicate detection, noise ratio, coverage).

---

## Phase 4: Synthesize Stage

### Task 11: Instruction pair generator

**Files:**
- Create: `adaptron/synthesize/__init__.py`
- Create: `adaptron/synthesize/base.py`
- Create: `adaptron/synthesize/instruction.py`
- Create: `tests/synthesize/test_instruction.py`

Implement `TemplateInstructionGenerator` that creates instruction/response pairs from chunks using templates. Register with `@register_plugin("synthesizer", "instruction")`.

---

## Phase 5: Train Stage

### Task 12: QLoRA trainer

**Files:**
- Create: `adaptron/train/__init__.py`
- Create: `adaptron/train/base.py`
- Create: `adaptron/train/models.py`
- Create: `adaptron/train/qlora.py`
- Create: `tests/train/test_qlora.py`

Implement `QLoRATrainer` with Unsloth acceleration + HuggingFace PEFT fallback. Register with `@register_plugin("trainer", "qlora")`.

---

## Phase 6: Evaluate Stage

### Task 13: Domain evaluator

**Files:**
- Create: `adaptron/evaluate/__init__.py`
- Create: `adaptron/evaluate/base.py`
- Create: `adaptron/evaluate/domain.py`
- Create: `tests/evaluate/test_domain.py`

Implement `DomainEvaluator` with exact match scoring. Register with `@register_plugin("evaluator", "domain")`.

---

## Phase 7: Deploy Stage

### Task 14: Ollama and GGUF deployers

**Files:**
- Create: `adaptron/deploy/__init__.py`
- Create: `adaptron/deploy/base.py`
- Create: `adaptron/deploy/ollama.py`
- Create: `adaptron/deploy/gguf.py`
- Create: `tests/deploy/test_ollama.py`

Implement `OllamaDeployer` (Modelfile generation, ollama create, serve) and `GGUFDeployer` (llama.cpp quantization).

---

## Phase 8: RAG Module

### Task 15: ChromaDB indexer and retriever

**Files:**
- Create: `adaptron/rag/__init__.py`
- Create: `adaptron/rag/indexer.py`
- Create: `adaptron/rag/retriever.py`
- Create: `tests/rag/test_rag.py`

Implement `ChromaIndexer` and `ChromaRetriever` using ChromaDB.

---

## Phase 9: CLI

### Task 16: Typer CLI

**Files:**
- Create: `adaptron/cli/__init__.py`
- Create: `adaptron/cli/main.py`
- Create: `tests/cli/test_cli.py`

Implement `version`, `init`, `run`, and `wizard` commands.

---

## Phase 10: FastAPI Backend

### Task 17: API with wizard and pipeline endpoints

**Files:**
- Create: `adaptron/api/__init__.py`
- Create: `adaptron/api/main.py`
- Create: `adaptron/api/routes/wizard.py`
- Create: `adaptron/api/routes/pipelines.py`
- Create: `tests/api/test_api.py`

Implement health check, `POST /api/wizard/recommend`, `POST /api/pipelines/start`, `GET /api/pipelines/{id}`.

---

## Phase 11: Next.js Frontend

### Task 18: Initialize Next.js and port wizard

**Files:**
- Create: `web/` with Next.js scaffolding

Port the 7-step wizard from `localmind-wizard.html` to React/Next.js with Tailwind. Add dashboard page for pipeline monitoring.

---

## Phase 12: Integration & Remaining Tasks

### Task 19: Pipeline factory

Wire `PipelineFactory.create(config)` to assemble stages from registry.

### Task 20: HuggingFace Hub deployer

### Task 21: Full FT, CPT, Distillation, DPO trainers

### Task 22: Schema inference analyzer

### Task 23: DOCX and CSV ingesters

### Task 24: End-to-end integration test

### Task 25: Update README with docs
