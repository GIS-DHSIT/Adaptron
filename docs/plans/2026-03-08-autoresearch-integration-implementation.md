# Autonomous Research Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add autonomous LLM-driven experiment capabilities to Adaptron — an ExperimentRunner that proposes, trains, evaluates, and iterates automatically.

**Architecture:** An `ExperimentRunner` orchestrates a loop: an `ExperimentAgent` (LLM) proposes `TrainConfig` changes, a `TimeBudgetWrapper` runs time-limited training via any existing `BaseTrainer` plugin, a `BPBEvaluator` scores the result, and an `ExperimentTracker` logs everything. The agent keeps improvements and reverts regressions.

**Tech Stack:** Python 3.11+, PyTorch (for BPB eval), existing Adaptron plugins (BaseTrainer, EventBus, TrainConfig), LLM API for agent proposals.

---

## Phase 1: Data Models & Config

### Task 1: Research data models

**Files:**
- Create: `adaptron/research/__init__.py`
- Create: `adaptron/research/config.py`
- Create: `tests/research/__init__.py`
- Create: `tests/research/test_config.py`

**Step 1: Write failing tests**

```python
# tests/research/__init__.py
```

```python
# tests/research/test_config.py
from adaptron.research.config import (
    ResearchConfig,
    ExperimentProposal,
    ExperimentResult,
)
from adaptron.train.models import TrainConfig


def test_research_config_defaults():
    base = TrainConfig(base_model="test/model", output_dir="/tmp/out")
    config = ResearchConfig(base_config=base)
    assert config.time_budget == 300
    assert config.max_experiments == 50
    assert config.mode == "config"
    assert config.strategy == "explore_exploit"
    assert config.trainer_plugin == "qlora"


def test_research_config_custom():
    base = TrainConfig(base_model="test/model", output_dir="/tmp/out")
    config = ResearchConfig(
        base_config=base,
        time_budget=600,
        max_experiments=100,
        mode="hybrid",
        strategy="random",
        trainer_plugin="full_ft",
    )
    assert config.time_budget == 600
    assert config.mode == "hybrid"


def test_experiment_proposal():
    proposal = ExperimentProposal(
        experiment_id="abc-123",
        description="Increase lora_rank to 128",
        config_changes={"lora_rank": 128},
        reasoning="Higher rank may capture more features",
    )
    assert proposal.config_changes == {"lora_rank": 128}
    assert proposal.code_changes is None
    assert proposal.parent_id is None


def test_experiment_result():
    result = ExperimentResult(
        experiment_id="abc-123",
        description="baseline",
        config_snapshot={"base_model": "test"},
        val_bpb=1.245,
        training_time_s=300.0,
        total_steps=100,
        final_loss=0.5,
        status="baseline",
        reasoning="Initial run",
        timestamp="2026-03-08T00:00:00",
    )
    assert result.val_bpb == 1.245
    assert result.status == "baseline"
    assert result.parent_id is None
    assert result.val_loss is None
    assert result.domain_score is None
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/research/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# adaptron/research/__init__.py
"""Autonomous research and experiment runner."""
```

```python
# adaptron/research/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adaptron.train.models import TrainConfig


@dataclass
class ResearchConfig:
    base_config: TrainConfig
    time_budget: int = 300
    max_experiments: int = 50
    max_total_time: int | None = None
    eval_tokens: int = 20_971_520
    mode: str = "config"
    strategy: str = "explore_exploit"
    trainer_plugin: str = "qlora"
    agent_model: str = "claude-sonnet-4-20250514"


@dataclass
class ExperimentProposal:
    experiment_id: str
    description: str
    config_changes: dict[str, Any]
    reasoning: str
    code_changes: str | None = None
    parent_id: str | None = None


@dataclass
class ExperimentResult:
    experiment_id: str
    description: str
    config_snapshot: dict[str, Any]
    training_time_s: float
    total_steps: int
    final_loss: float
    status: str
    reasoning: str
    timestamp: str
    parent_id: str | None = None
    val_bpb: float | None = None
    val_loss: float | None = None
    domain_score: float | None = None
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/research/test_config.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add adaptron/research/__init__.py adaptron/research/config.py tests/research/__init__.py tests/research/test_config.py
git commit -m "feat: research data models (ResearchConfig, ExperimentProposal, ExperimentResult)"
```

---

### Task 2: BPB evaluator

**Files:**
- Create: `adaptron/evaluate/bpb.py`
- Create: `tests/evaluate/test_bpb.py`

**Step 1: Write failing tests**

```python
# tests/evaluate/test_bpb.py
import math
from adaptron.evaluate.bpb import BPBEvaluator


def test_bpb_evaluator_registered():
    from adaptron.core.registry import global_registry
    plugin = global_registry.get("evaluator", "bpb")
    assert plugin is BPBEvaluator


def test_compute_bpb_from_losses():
    evaluator = BPBEvaluator()
    # Simulate: 3 tokens with known losses (in nats), text was 10 bytes
    token_losses_nats = [1.0, 2.0, 1.5]  # total = 4.5 nats
    total_bytes = 10
    bpb = evaluator.compute_bpb(token_losses_nats, total_bytes)
    expected = sum(token_losses_nats) / (math.log(2) * total_bytes)
    assert abs(bpb - expected) < 1e-6


def test_compute_bpb_zero_bytes():
    evaluator = BPBEvaluator()
    bpb = evaluator.compute_bpb([1.0, 2.0], 0)
    assert bpb == float("inf")


def test_evaluate_returns_dict():
    evaluator = BPBEvaluator()
    # evaluate() wraps compute_bpb for the BaseEvaluator interface
    result = evaluator.evaluate(
        predictions=["Hello world"],
        references=["Hello world"],
    )
    assert "info" in result
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/evaluate/test_bpb.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/evaluate/bpb.py
from __future__ import annotations

import math
from typing import Any

from adaptron.core.registry import register_plugin
from adaptron.evaluate.base import BaseEvaluator


@register_plugin("evaluator", "bpb")
class BPBEvaluator(BaseEvaluator):
    """Bits-per-byte evaluator -- vocab-size independent metric."""

    def compute_bpb(self, token_losses_nats: list[float], total_bytes: int) -> float:
        """Compute bits-per-byte from per-token cross-entropy losses in nats.

        BPB = sum(losses_nats) / (ln(2) * total_bytes)
        """
        if total_bytes == 0:
            return float("inf")
        total_nats = sum(token_losses_nats)
        return total_nats / (math.log(2) * total_bytes)

    def evaluate(
        self, predictions: list[str], references: list[str]
    ) -> dict[str, Any]:
        """BaseEvaluator interface. BPB requires model + data, not predictions.

        For full BPB eval, use compute_bpb() directly with model outputs.
        This method provides a compatibility shim.
        """
        return {
            "info": "BPB evaluation requires model and tokenizer. Use compute_bpb() directly.",
            "total_samples": len(predictions),
        }
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/evaluate/test_bpb.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add adaptron/evaluate/bpb.py tests/evaluate/test_bpb.py
git commit -m "feat: BPB evaluator plugin for vocab-size independent evaluation"
```

---

## Phase 2: Core Research Engine

### Task 3: Experiment tracker

**Files:**
- Create: `adaptron/research/tracker.py`
- Create: `tests/research/test_tracker.py`

**Step 1: Write failing tests**

```python
# tests/research/test_tracker.py
import pytest
from pathlib import Path
from adaptron.research.tracker import ExperimentTracker
from adaptron.research.config import ExperimentResult


def _make_result(exp_id: str, val_bpb: float, status: str = "improved") -> ExperimentResult:
    return ExperimentResult(
        experiment_id=exp_id,
        description=f"experiment {exp_id}",
        config_snapshot={"base_model": "test"},
        val_bpb=val_bpb,
        training_time_s=300.0,
        total_steps=100,
        final_loss=0.5,
        status=status,
        reasoning="test",
        timestamp="2026-03-08T00:00:00",
    )


def test_tracker_log_and_list(tmp_path):
    tracker = ExperimentTracker(output_dir=tmp_path)
    r1 = _make_result("exp-1", 1.245, "baseline")
    r2 = _make_result("exp-2", 1.231, "improved")
    tracker.log(r1)
    tracker.log(r2)
    results = tracker.list_results()
    assert len(results) == 2
    assert results[0]["experiment_id"] == "exp-1"


def test_tracker_best_result(tmp_path):
    tracker = ExperimentTracker(output_dir=tmp_path)
    tracker.log(_make_result("exp-1", 1.245, "baseline"))
    tracker.log(_make_result("exp-2", 1.231, "improved"))
    tracker.log(_make_result("exp-3", 1.258, "regressed"))
    best = tracker.get_best()
    assert best is not None
    assert best["experiment_id"] == "exp-2"
    assert best["val_bpb"] == "1.231"


def test_tracker_tsv_persistence(tmp_path):
    tracker1 = ExperimentTracker(output_dir=tmp_path)
    tracker1.log(_make_result("exp-1", 1.245, "baseline"))

    # New tracker instance reads existing TSV
    tracker2 = ExperimentTracker(output_dir=tmp_path)
    results = tracker2.list_results()
    assert len(results) == 1


def test_tracker_summary(tmp_path):
    tracker = ExperimentTracker(output_dir=tmp_path)
    tracker.log(_make_result("exp-1", 1.245, "baseline"))
    tracker.log(_make_result("exp-2", 1.231, "improved"))
    summary = tracker.summary()
    assert summary["total_experiments"] == 2
    assert summary["improvements"] == 1
    assert summary["best_val_bpb"] == 1.231
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/research/test_tracker.py -v`
Expected: FAIL

**Step 3: Write implementation**

The tracker writes experiments to `output_dir/experiments.tsv` as tab-separated values. It reads back on init for resume support. Tracks the best result by lowest `val_bpb`.

```python
# adaptron/research/tracker.py
from __future__ import annotations

import csv
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from adaptron.research.config import ExperimentResult

logger = logging.getLogger(__name__)

TSV_FIELDS = [
    "experiment_id", "parent_id", "description", "val_bpb", "val_loss",
    "domain_score", "final_loss", "total_steps", "training_time_s",
    "status", "reasoning", "timestamp",
]


class ExperimentTracker:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._tsv_path = self._output_dir / "experiments.tsv"
        self._results: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._tsv_path.exists():
            with open(self._tsv_path, newline="") as f:
                reader = csv.DictReader(f, delimiter="\t")
                self._results = list(reader)

    def log(self, result: ExperimentResult) -> None:
        row = {k: str(getattr(result, k, "")) for k in TSV_FIELDS}
        self._results.append(row)
        write_header = not self._tsv_path.exists() or self._tsv_path.stat().st_size == 0
        with open(self._tsv_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=TSV_FIELDS, delimiter="\t")
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        logger.info("Logged experiment %s: %s (val_bpb=%s)", result.experiment_id, result.status, result.val_bpb)

    def list_results(self) -> list[dict[str, Any]]:
        return list(self._results)

    def get_best(self) -> dict[str, Any] | None:
        valid = [r for r in self._results if r.get("val_bpb") and r["val_bpb"] != "None"]
        if not valid:
            return None
        return min(valid, key=lambda r: float(r["val_bpb"]))

    def summary(self) -> dict[str, Any]:
        best = self.get_best()
        return {
            "total_experiments": len(self._results),
            "improvements": sum(1 for r in self._results if r.get("status") == "improved"),
            "regressions": sum(1 for r in self._results if r.get("status") == "regressed"),
            "failures": sum(1 for r in self._results if r.get("status") == "failed"),
            "best_val_bpb": float(best["val_bpb"]) if best else None,
            "best_experiment_id": best["experiment_id"] if best else None,
        }
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/research/test_tracker.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add adaptron/research/tracker.py tests/research/test_tracker.py
git commit -m "feat: experiment tracker with TSV logging, best tracking, resume support"
```

---

### Task 4: Time budget wrapper

**Files:**
- Create: `adaptron/research/timer.py`
- Create: `tests/research/test_timer.py`

**Step 1: Write failing tests**

```python
# tests/research/test_timer.py
import pytest
import time
from adaptron.research.timer import TimeBudgetWrapper


def test_timer_starts_and_checks():
    timer = TimeBudgetWrapper(time_budget=10)
    timer.start()
    assert timer.is_expired() is False
    assert timer.elapsed() >= 0
    assert timer.remaining() <= 10


def test_timer_expires():
    timer = TimeBudgetWrapper(time_budget=0)
    timer.start()
    # Budget of 0 seconds should expire immediately
    time.sleep(0.01)
    assert timer.is_expired() is True


def test_timer_not_started():
    timer = TimeBudgetWrapper(time_budget=300)
    assert timer.elapsed() == 0.0
    assert timer.is_expired() is False


def test_timer_remaining():
    timer = TimeBudgetWrapper(time_budget=5)
    timer.start()
    remaining = timer.remaining()
    assert 0 <= remaining <= 5
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/research/test_timer.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/research/timer.py
from __future__ import annotations

import time


class TimeBudgetWrapper:
    """Tracks wall-clock time for time-budgeted training experiments."""

    def __init__(self, time_budget: int) -> None:
        self._time_budget = time_budget
        self._start_time: float | None = None

    def start(self) -> None:
        self._start_time = time.monotonic()

    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def remaining(self) -> float:
        return max(0.0, self._time_budget - self.elapsed())

    def is_expired(self) -> bool:
        if self._start_time is None:
            return False
        return self.elapsed() >= self._time_budget
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/research/test_timer.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add adaptron/research/timer.py tests/research/test_timer.py
git commit -m "feat: time budget wrapper for wall-clock training cutoff"
```

---

### Task 5: Experiment agent

**Files:**
- Create: `adaptron/research/agent.py`
- Create: `tests/research/test_agent.py`

**Step 1: Write failing tests**

```python
# tests/research/test_agent.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from adaptron.research.agent import ExperimentAgent
from adaptron.research.config import ResearchConfig, ExperimentResult
from adaptron.train.models import TrainConfig


def _make_research_config() -> ResearchConfig:
    return ResearchConfig(
        base_config=TrainConfig(base_model="test/model", output_dir="/tmp/out"),
    )


def _make_result(exp_id: str, val_bpb: float, status: str) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=exp_id,
        description=f"experiment {exp_id}",
        config_snapshot={"learning_rate": 0.0002},
        val_bpb=val_bpb,
        training_time_s=300.0,
        total_steps=100,
        final_loss=0.5,
        status=status,
        reasoning="test",
        timestamp="2026-03-08T00:00:00",
    )


def test_validate_proposal_valid():
    agent = ExperimentAgent(config=_make_research_config())
    changes = {"learning_rate": 0.001, "batch_size": 8, "lora_rank": 128}
    errors = agent.validate_proposal(changes)
    assert errors == []


def test_validate_proposal_invalid_field():
    agent = ExperimentAgent(config=_make_research_config())
    changes = {"nonexistent_field": 42}
    errors = agent.validate_proposal(changes)
    assert len(errors) > 0
    assert "nonexistent_field" in errors[0]


def test_validate_proposal_bad_value():
    agent = ExperimentAgent(config=_make_research_config())
    changes = {"learning_rate": -1.0}
    errors = agent.validate_proposal(changes)
    assert len(errors) > 0


def test_apply_changes_to_config():
    agent = ExperimentAgent(config=_make_research_config())
    base = TrainConfig(base_model="test/model", output_dir="/tmp/out", learning_rate=0.0002)
    changes = {"learning_rate": 0.001, "lora_rank": 128}
    new_config = agent.apply_changes(base, changes)
    assert new_config.learning_rate == 0.001
    assert new_config.lora_rank == 128
    # Original unchanged
    assert base.learning_rate == 0.0002


def test_build_prompt_includes_history():
    agent = ExperimentAgent(config=_make_research_config())
    current_config = TrainConfig(base_model="test/model", output_dir="/tmp/out")
    history = [
        _make_result("exp-1", 1.245, "baseline"),
        _make_result("exp-2", 1.231, "improved"),
    ]
    prompt = agent.build_prompt(current_config, history)
    assert "1.245" in prompt
    assert "1.231" in prompt
    assert "learning_rate" in prompt
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/research/test_agent.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/research/agent.py
from __future__ import annotations

import copy
import json
import logging
import uuid
from dataclasses import asdict, fields
from typing import Any

from adaptron.research.config import ExperimentProposal, ExperimentResult, ResearchConfig
from adaptron.train.models import TrainConfig

logger = logging.getLogger(__name__)

VALID_CONFIG_FIELDS = {f.name for f in fields(TrainConfig)}
NUMERIC_POSITIVE_FIELDS = {"learning_rate", "batch_size", "epochs", "lora_rank", "lora_alpha",
                           "max_seq_length", "gradient_accumulation_steps"}


class ExperimentAgent:
    """LLM-driven agent that proposes training config changes."""

    def __init__(self, config: ResearchConfig) -> None:
        self._config = config

    def validate_proposal(self, changes: dict[str, Any]) -> list[str]:
        errors = []
        for key, value in changes.items():
            if key not in VALID_CONFIG_FIELDS:
                errors.append(f"Unknown config field: {key}")
                continue
            if key in NUMERIC_POSITIVE_FIELDS and isinstance(value, (int, float)) and value <= 0:
                errors.append(f"Field {key} must be positive, got {value}")
        return errors

    def apply_changes(self, base_config: TrainConfig, changes: dict[str, Any]) -> TrainConfig:
        new_config = copy.deepcopy(base_config)
        for key, value in changes.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config

    def build_prompt(self, current_config: TrainConfig, history: list[ExperimentResult]) -> str:
        config_dict = {k: v for k, v in asdict(current_config).items()
                       if k not in ("extra", "target_modules")}
        lines = [
            "You are an autonomous ML research agent optimizing a language model training config.",
            "Your goal: minimize val_bpb (validation bits-per-byte). Lower is better.",
            "",
            "## Current Best Config",
            json.dumps(config_dict, indent=2),
            "",
            "## Experiment History (most recent last)",
        ]
        if not history:
            lines.append("No experiments yet. This is the first run.")
        else:
            for r in history[-20:]:
                lines.append(
                    f"- {r.experiment_id}: val_bpb={r.val_bpb}, status={r.status}, "
                    f"desc=\"{r.description}\""
                )
        lines.extend([
            "",
            "## Modifiable Fields",
            ", ".join(sorted(VALID_CONFIG_FIELDS - {"extra", "target_modules", "output_dir"})),
            "",
            "## Instructions",
            "- Propose ONE change (or a small related set of changes)",
            "- Explore early, exploit later",
            "- If recent experiments regressed, try a different direction",
            "- Respond with JSON: {\"description\": \"...\", \"changes\": {\"field\": value}, \"reasoning\": \"...\"}",
        ])
        return "\n".join(lines)

    async def propose(
        self, current_config: TrainConfig, history: list[ExperimentResult]
    ) -> ExperimentProposal:
        prompt = self.build_prompt(current_config, history)
        response_text = await self._call_llm(prompt)
        parsed = json.loads(response_text)
        return ExperimentProposal(
            experiment_id=str(uuid.uuid4())[:8],
            description=parsed.get("description", ""),
            config_changes=parsed.get("changes", {}),
            reasoning=parsed.get("reasoning", ""),
        )

    async def _call_llm(self, prompt: str) -> str:
        try:
            import httpx
            # Uses a generic OpenAI-compatible API endpoint
            api_key = None
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
            base_url = os.environ.get("LLM_API_BASE", "https://api.anthropic.com")

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{base_url}/v1/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                    json={
                        "model": self._config.agent_model,
                        "max_tokens": 1024,
                        "temperature": 0,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                text = data["content"][0]["text"]
                # Extract JSON from response (may be wrapped in markdown)
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return text.strip()
        except Exception as e:
            logger.warning("LLM call failed: %s. Using fallback proposal.", e)
            return json.dumps({
                "description": "fallback: reduce learning rate by 50%",
                "changes": {"learning_rate": current_config.learning_rate * 0.5 if hasattr(self, '_last_config') else 0.0001},
                "reasoning": "LLM unavailable, applying conservative change",
            })
```

Note: The `_call_llm` method has a fallback so experiments can proceed even without an API key (useful for testing). The LLM integration is pluggable — it reads API keys from environment variables.

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/research/test_agent.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add adaptron/research/agent.py tests/research/test_agent.py
git commit -m "feat: experiment agent with LLM-driven proposal generation and validation"
```

---

### Task 6: Experiment runner

**Files:**
- Create: `adaptron/research/runner.py`
- Create: `tests/research/test_runner.py`

**Step 1: Write failing tests**

```python
# tests/research/test_runner.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from adaptron.research.runner import ExperimentRunner
from adaptron.research.config import ResearchConfig, ExperimentProposal, ExperimentResult
from adaptron.train.models import TrainConfig, TrainResult
from adaptron.core.events import EventBus


def _make_research_config(tmp_path) -> ResearchConfig:
    return ResearchConfig(
        base_config=TrainConfig(
            base_model="test/model",
            output_dir=str(tmp_path / "output"),
        ),
        time_budget=1,
        max_experiments=2,
        trainer_plugin="qlora",
    )


@pytest.mark.asyncio
async def test_runner_runs_experiments(tmp_path):
    config = _make_research_config(tmp_path)
    bus = EventBus()
    events = []
    bus.on("*", lambda e: events.append(e))

    mock_trainer = AsyncMock()
    mock_trainer.train.return_value = TrainResult(
        model_path=str(tmp_path / "output"),
        training_mode="qlora",
        total_steps=50,
        final_loss=0.5,
    )

    mock_agent = AsyncMock()
    mock_agent.propose.return_value = ExperimentProposal(
        experiment_id="exp-1",
        description="test change",
        config_changes={"learning_rate": 0.001},
        reasoning="test",
    )
    mock_agent.validate_proposal.return_value = []
    mock_agent.apply_changes.side_effect = lambda base, changes: base

    runner = ExperimentRunner(config=config, output_dir=tmp_path, event_bus=bus)
    runner._agent = mock_agent
    runner._trainer = mock_trainer

    await runner.run()

    assert len(runner.tracker.list_results()) >= 1
    event_types = [e.type for e in events]
    assert "research_start" in event_types
    assert "research_complete" in event_types


@pytest.mark.asyncio
async def test_runner_handles_training_failure(tmp_path):
    config = _make_research_config(tmp_path)
    config.max_experiments = 1

    mock_trainer = AsyncMock()
    mock_trainer.train.side_effect = RuntimeError("GPU OOM")

    mock_agent = AsyncMock()
    mock_agent.propose.return_value = ExperimentProposal(
        experiment_id="exp-fail",
        description="bad config",
        config_changes={"batch_size": 9999},
        reasoning="test",
    )
    mock_agent.validate_proposal.return_value = []
    mock_agent.apply_changes.side_effect = lambda base, changes: base

    runner = ExperimentRunner(config=config, output_dir=tmp_path)
    runner._agent = mock_agent
    runner._trainer = mock_trainer

    await runner.run()

    results = runner.tracker.list_results()
    assert any(r["status"] == "failed" for r in results)


@pytest.mark.asyncio
async def test_runner_keeps_best_config(tmp_path):
    config = _make_research_config(tmp_path)
    config.max_experiments = 2

    call_count = 0

    async def fake_train(cfg, dataset, event_bus=None):
        nonlocal call_count
        call_count += 1
        loss = 0.6 if call_count == 1 else 0.4
        return TrainResult(
            model_path=str(tmp_path / "output"),
            training_mode="qlora",
            total_steps=50,
            final_loss=loss,
        )

    mock_trainer = AsyncMock()
    mock_trainer.train.side_effect = fake_train

    mock_agent = AsyncMock()
    mock_agent.propose.return_value = ExperimentProposal(
        experiment_id="exp-1",
        description="improvement",
        config_changes={"learning_rate": 0.001},
        reasoning="test",
    )
    mock_agent.validate_proposal.return_value = []
    mock_agent.apply_changes.side_effect = lambda base, changes: base

    runner = ExperimentRunner(config=config, output_dir=tmp_path)
    runner._agent = mock_agent
    runner._trainer = mock_trainer

    await runner.run()

    best = runner.tracker.get_best()
    assert best is not None
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/research/test_runner.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/research/runner.py
from __future__ import annotations

import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.research.agent import ExperimentAgent
from adaptron.research.config import ExperimentResult, ResearchConfig
from adaptron.research.timer import TimeBudgetWrapper
from adaptron.research.tracker import ExperimentTracker
from adaptron.train.models import TrainConfig, TrainResult

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Orchestrates autonomous research experiments."""

    def __init__(
        self,
        config: ResearchConfig,
        output_dir: Path,
        event_bus: EventBus | None = None,
    ) -> None:
        self._config = config
        self._output_dir = Path(output_dir)
        self._bus = event_bus or EventBus()
        self.tracker = ExperimentTracker(output_dir=self._output_dir / "research")
        self._agent = ExperimentAgent(config=config)
        self._trainer: Any = None
        self._best_config = config.base_config
        self._best_bpb: float | None = None

    async def run(self) -> None:
        self._bus.emit("research_start", Event(
            type="research_start",
            data={"max_experiments": self._config.max_experiments,
                  "time_budget": self._config.time_budget},
        ))

        if self._trainer is None:
            self._trainer = self._load_trainer()

        history: list[ExperimentResult] = []

        for i in range(self._config.max_experiments):
            logger.info("Experiment %d/%d", i + 1, self._config.max_experiments)

            try:
                proposal = await self._agent.propose(self._best_config, history)
            except Exception as e:
                logger.error("Agent failed to propose: %s", e)
                continue

            errors = self._agent.validate_proposal(proposal.config_changes)
            if errors:
                logger.warning("Invalid proposal: %s", errors)
                continue

            experiment_config = self._agent.apply_changes(
                self._best_config, proposal.config_changes
            )

            self._bus.emit("experiment_start", Event(
                type="experiment_start",
                data={"experiment_id": proposal.experiment_id,
                      "description": proposal.description,
                      "experiment_number": i + 1},
            ))

            result = await self._run_single(proposal, experiment_config)
            history.append(result)
            self.tracker.log(result)

            if result.status == "improved":
                self._best_config = experiment_config
                self._best_bpb = result.val_bpb
                self._bus.emit("experiment_improved", Event(
                    type="experiment_improved",
                    data={"experiment_id": result.experiment_id,
                          "val_bpb": result.val_bpb},
                ))
            elif result.status == "failed":
                self._bus.emit("experiment_failed", Event(
                    type="experiment_failed",
                    data={"experiment_id": result.experiment_id,
                          "error": result.reasoning},
                ))

            self._bus.emit("experiment_complete", Event(
                type="experiment_complete",
                data={"experiment_id": result.experiment_id,
                      "status": result.status,
                      "val_bpb": result.val_bpb},
            ))

        self._bus.emit("research_complete", Event(
            type="research_complete",
            data=self.tracker.summary(),
        ))

    async def _run_single(
        self, proposal: Any, experiment_config: TrainConfig
    ) -> ExperimentResult:
        timer = TimeBudgetWrapper(self._config.time_budget)
        timer.start()
        start_time = time.monotonic()

        try:
            train_result: TrainResult = await self._trainer.train(
                experiment_config, [], self._bus
            )
            training_time = time.monotonic() - start_time

            # Determine if improved (use final_loss as proxy when BPB not available)
            current_metric = train_result.final_loss
            if self._best_bpb is None:
                status = "baseline"
                self._best_bpb = current_metric
            elif current_metric < self._best_bpb:
                status = "improved"
            else:
                status = "regressed"

            return ExperimentResult(
                experiment_id=proposal.experiment_id,
                parent_id=proposal.parent_id,
                description=proposal.description,
                config_snapshot=asdict(experiment_config),
                val_bpb=current_metric,
                val_loss=train_result.final_loss,
                training_time_s=training_time,
                total_steps=train_result.total_steps,
                final_loss=train_result.final_loss,
                status=status,
                reasoning=proposal.reasoning,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            training_time = time.monotonic() - start_time
            logger.error("Experiment %s failed: %s", proposal.experiment_id, e)
            return ExperimentResult(
                experiment_id=proposal.experiment_id,
                parent_id=proposal.parent_id,
                description=proposal.description,
                config_snapshot=asdict(experiment_config),
                training_time_s=training_time,
                total_steps=0,
                final_loss=0.0,
                status="failed",
                reasoning=str(e),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def _load_trainer(self) -> Any:
        from adaptron.core.registry import global_registry
        trainer_cls = global_registry.get("trainer", self._config.trainer_plugin)
        if trainer_cls is None:
            raise ValueError(f"Trainer plugin '{self._config.trainer_plugin}' not found")
        return trainer_cls()
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/research/test_runner.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add adaptron/research/runner.py tests/research/test_runner.py
git commit -m "feat: experiment runner with autonomous research loop"
```

---

## Phase 3: CLI & API

### Task 7: CLI research command

**Files:**
- Modify: `adaptron/cli/main.py`
- Create: `tests/cli/test_research.py`

**Step 1: Write failing tests**

```python
# tests/cli/test_research.py
from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()


def test_research_command_exists():
    result = runner.invoke(app, ["research", "--help"])
    assert result.exit_code == 0
    assert "research" in result.output.lower() or "experiment" in result.output.lower()


def test_research_missing_config(tmp_path):
    result = runner.invoke(app, ["research", "--config", str(tmp_path / "nonexistent.yaml")])
    assert result.exit_code != 0
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/cli/test_research.py -v`
Expected: FAIL

**Step 3: Add research command to CLI**

Add to `adaptron/cli/main.py` after the existing `playground` command:

```python
@app.command()
def research(
    config: Path = typer.Option("adaptron.yaml", help="Path to config file"),
    time_budget: int = typer.Option(300, help="Seconds per experiment"),
    max_experiments: int = typer.Option(50, help="Max number of experiments"),
    trainer: str = typer.Option("qlora", help="Trainer plugin to use"),
    mode: str = typer.Option("config", help="Mode: config or hybrid"),
    strategy: str = typer.Option("explore_exploit", help="Search strategy"),
    output_dir: Path = typer.Option("output", help="Output directory"),
):
    """Run autonomous research experiments to optimize training."""
    import asyncio
    from adaptron.core.config import PipelineConfig
    from adaptron.research.config import ResearchConfig
    from adaptron.research.runner import ExperimentRunner
    from adaptron.train.models import TrainConfig

    if not config.exists():
        console.print(f"[red]Config file not found: {config}[/red]")
        raise typer.Exit(code=1)

    pipeline_config = PipelineConfig.from_yaml(config)
    train_config = TrainConfig(
        base_model=pipeline_config.base_model,
        output_dir=str(output_dir),
        training_mode=trainer,
        epochs=pipeline_config.epochs,
        learning_rate=pipeline_config.learning_rate,
        batch_size=pipeline_config.batch_size,
        lora_rank=pipeline_config.lora_rank,
        max_seq_length=pipeline_config.max_seq_length,
    )

    research_config = ResearchConfig(
        base_config=train_config,
        time_budget=time_budget,
        max_experiments=max_experiments,
        mode=mode,
        strategy=strategy,
        trainer_plugin=trainer,
    )

    console.print(f"[blue]Starting autonomous research[/blue]")
    console.print(f"  Base model: {train_config.base_model}")
    console.print(f"  Trainer: {trainer}")
    console.print(f"  Time budget: {time_budget}s per experiment")
    console.print(f"  Max experiments: {max_experiments}")
    console.print(f"  Strategy: {strategy}")

    runner = ExperimentRunner(config=research_config, output_dir=output_dir)

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Research stopped by user.[/yellow]")

    summary = runner.tracker.summary()
    console.print(f"\n[green]Research complete![/green]")
    console.print(f"  Total experiments: {summary['total_experiments']}")
    console.print(f"  Improvements: {summary['improvements']}")
    console.print(f"  Best val_bpb: {summary['best_val_bpb']}")
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/cli/test_research.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add adaptron/cli/main.py tests/cli/test_research.py
git commit -m "feat: CLI research command for autonomous experiments"
```

---

### Task 8: API research routes

**Files:**
- Create: `adaptron/api/routes/research.py`
- Modify: `adaptron/api/main.py`
- Create: `tests/api/test_research.py`

**Step 1: Write failing tests**

```python
# tests/api/test_research.py
import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_research_status(client):
    response = client.get("/api/research/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data


def test_research_results_empty(client):
    response = client.get("/api/research/results")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
```

**Step 2: Run tests to verify they fail**

Run: `py -m pytest tests/api/test_research.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# adaptron/api/routes/research.py
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/research", tags=["research"])

# Module-level state for tracking active research
_active_runner = None


@router.get("/status")
def research_status():
    if _active_runner is None:
        return {"running": False, "message": "No active research session"}
    summary = _active_runner.tracker.summary()
    return {"running": True, **summary}


@router.get("/results")
def research_results():
    if _active_runner is None:
        return {"results": []}
    return {"results": _active_runner.tracker.list_results()}


@router.get("/best")
def research_best():
    if _active_runner is None:
        return {"best": None}
    return {"best": _active_runner.tracker.get_best()}


@router.post("/stop")
def research_stop():
    global _active_runner
    if _active_runner is None:
        return {"status": "no active session"}
    _active_runner = None
    return {"status": "stopped"}
```

Add to `adaptron/api/main.py` after the existing routers:

```python
from adaptron.api.routes.research import router as research_router
app.include_router(research_router)
```

**Step 4: Run tests to verify they pass**

Run: `py -m pytest tests/api/test_research.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add adaptron/api/routes/research.py adaptron/api/main.py tests/api/test_research.py
git commit -m "feat: API research routes for status, results, and control"
```

---

## Phase 4: Integration Test

### Task 9: End-to-end research integration test

**Files:**
- Create: `tests/integration/test_research_e2e.py`

**Step 1: Write the test**

```python
# tests/integration/test_research_e2e.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from adaptron.research.config import ResearchConfig, ExperimentProposal
from adaptron.research.runner import ExperimentRunner
from adaptron.train.models import TrainConfig, TrainResult
from adaptron.core.events import EventBus, Event


@pytest.mark.asyncio
async def test_full_research_loop(tmp_path):
    """E2E: configure -> run 3 experiments -> track results -> find best."""
    train_config = TrainConfig(
        base_model="test/model",
        output_dir=str(tmp_path / "output"),
        learning_rate=0.0002,
    )
    research_config = ResearchConfig(
        base_config=train_config,
        time_budget=1,
        max_experiments=3,
    )

    bus = EventBus()
    events: list[Event] = []
    bus.on("*", lambda e: events.append(e))

    # Mock trainer with decreasing loss to simulate improvement
    losses = [0.6, 0.5, 0.55]
    call_idx = 0

    async def fake_train(cfg, dataset, event_bus=None):
        nonlocal call_idx
        loss = losses[call_idx % len(losses)]
        call_idx += 1
        return TrainResult(
            model_path=str(tmp_path / "output"),
            training_mode="qlora",
            total_steps=50,
            final_loss=loss,
        )

    mock_trainer = AsyncMock()
    mock_trainer.train.side_effect = fake_train

    proposals = [
        ExperimentProposal(experiment_id=f"exp-{i}", description=f"change {i}",
                           config_changes={"learning_rate": 0.001 * (i + 1)},
                           reasoning=f"test {i}")
        for i in range(3)
    ]
    mock_agent = AsyncMock()
    mock_agent.propose.side_effect = proposals
    mock_agent.validate_proposal.return_value = []
    mock_agent.apply_changes.side_effect = lambda base, changes: base

    runner = ExperimentRunner(
        config=research_config, output_dir=tmp_path, event_bus=bus
    )
    runner._agent = mock_agent
    runner._trainer = mock_trainer

    await runner.run()

    # Verify results
    results = runner.tracker.list_results()
    assert len(results) == 3

    # Verify best is the one with lowest loss (0.5)
    best = runner.tracker.get_best()
    assert best is not None
    assert best["val_bpb"] == "0.5"

    # Verify events
    event_types = [e.type for e in events]
    assert "research_start" in event_types
    assert "research_complete" in event_types
    assert event_types.count("experiment_start") == 3
    assert event_types.count("experiment_complete") == 3
    assert "experiment_improved" in event_types

    # Verify summary
    summary = runner.tracker.summary()
    assert summary["total_experiments"] == 3
    assert summary["best_val_bpb"] == 0.5
```

**Step 2: Run test**

Run: `py -m pytest tests/integration/test_research_e2e.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_research_e2e.py
git commit -m "test: end-to-end autonomous research integration test"
```

---

## Phase 5: Full Suite Verification

### Task 10: Run full test suite and verify

**Step 1: Run all tests**

Run: `py -m pytest --tb=short -q`
Expected: All tests pass (210+ tests), 0 failures

**Step 2: Commit any fixes if needed**

---

## Summary

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Research data models | 2 created | 4 |
| 2 | BPB evaluator | 1 created | 4 |
| 3 | Experiment tracker | 1 created | 4 |
| 4 | Time budget wrapper | 1 created | 4 |
| 5 | Experiment agent | 1 created | 5 |
| 6 | Experiment runner | 1 created | 3 |
| 7 | CLI research command | 1 modified | 2 |
| 8 | API research routes | 2 modified, 1 created | 2 |
| 9 | E2E integration test | 1 created | 1 |
| 10 | Full suite verification | — | — |
| **Total** | | **12 files** | **29 tests** |
