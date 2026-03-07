# Autonomous Research Integration Design

**Date:** 2026-03-08
**Status:** Approved
**Inspired by:** [karpathy/autoresearch](https://github.com/karpathy/autoresearch)

## Overview

Integrate autonomous LLM-driven experiment capabilities into Adaptron, inspired by Karpathy's autoresearch project. An `ExperimentRunner` lets users say "optimize this model overnight" — an LLM agent proposes training config changes, runs time-budgeted experiments, evaluates results, keeps improvements, reverts regressions, and iterates autonomously. Works with any existing Adaptron trainer plugin (QLoRA, Full FT, CPT, DPO, Distill).

## Architecture

```
adaptron research --config adaptron.yaml --time-budget 300 --max-experiments 50

                     ┌─────────────────────────────────────────┐
                     │         ExperimentRunner                 │
                     │                                         │
                     │  ┌──────────┐    ┌──────────────────┐   │
                     │  │ Research  │───>│  ExperimentAgent  │   │
                     │  │  Config   │    │  (LLM-driven)    │   │
                     │  └──────────┘    │  - propose()      │   │
                     │                  │  - analyze()      │   │
                     │                  └────────┬─────────┘   │
                     │                           │              │
                     │              ┌────────────▼───────────┐  │
                     │              │   Experiment Loop       │  │
                     │              │                         │  │
                     │              │  1. Agent proposes change│  │
                     │              │  2. Validate change      │  │
                     │              │  3. Train (time-budgeted)│  │
                     │              │  4. Evaluate (BPB+domain)│  │
                     │              │  5. Keep or revert       │  │
                     │              │  6. Log to tracker       │  │
                     │              │  7. Repeat               │  │
                     │              └────────────┬───────────┘  │
                     │                           │              │
                     │              ┌────────────▼───────────┐  │
                     │              │  ExperimentTracker      │  │
                     │              │  - TSV log              │  │
                     │              │  - EventBus streaming   │  │
                     │              │  - best result tracking │  │
                     │              └────────────────────────┘  │
                     └─────────────────────────────────────────┘
                                         │
                     Uses existing:  BaseTrainer (any plugin)
                                    DomainEvaluator + BPBEvaluator
                                    EventBus → WebSocket → UI
                                    TrainConfig mutations
```

## Components

### 1. ExperimentAgent — LLM-Driven Proposals

Operates in two modes (hybrid approach):

**Config mode (default):** Agent receives current `TrainConfig`, past experiment results, and proposes a new config as structured JSON. Can modify hyperparameters (learning_rate, batch_size, epochs, warmup_ratio, weight_decay), LoRA params (lora_rank, lora_alpha, lora_dropout, target_modules), model selection (base_model, max_seq_length), and training mode (qlora/full_ft/cpt/distill/dpo).

**Code mode (advanced, opt-in):** Agent can also modify a sandboxed `train_override.py` file. On failure, the file is reverted to the last working version automatically.

```python
@dataclass
class ExperimentProposal:
    experiment_id: str              # UUID
    description: str                # "Increase lora_rank to 128, halve learning rate"
    config_changes: dict[str, Any]  # {"lora_rank": 128, "learning_rate": 1e-4}
    code_changes: str | None        # Optional: modified train script content
    reasoning: str                  # Agent's reasoning for this change
    parent_id: str | None           # Which experiment this builds on
```

**LLM safeguards:**
- Temperature 0 for reproducibility
- Structured JSON output, parsed and validated
- Proposals validated before execution — no invalid fields, values within sane bounds
- Code changes are syntax-checked before running
- Agent receives: current best config + metrics, last N experiment results, search strategy hint

### 2. ResearchConfig

```python
@dataclass
class ResearchConfig:
    base_config: TrainConfig             # Starting training config
    time_budget: int = 300               # Seconds per experiment (default 5 min)
    max_experiments: int = 50            # Stop after N experiments
    max_total_time: int | None = None    # Optional: total wall-clock budget
    eval_tokens: int = 20_971_520        # ~20M tokens for BPB eval
    mode: str = "config"                 # "config" or "hybrid" (allows code edits)
    strategy: str = "explore_exploit"    # "explore_exploit", "random", "grid"
    trainer_plugin: str = "qlora"        # Which BaseTrainer to use
    agent_model: str = "claude-sonnet-4-20250514"  # LLM for proposals
```

### 3. Time-Budgeted Training

Wraps any existing `BaseTrainer` plugin. Instead of training for N epochs, it trains for N seconds of wall-clock time (excluding model loading/compilation). Enforced by a background timer that signals the trainer to stop gracefully. This makes experiments on different hardware comparable by normalizing on compute time.

### 4. BPB Evaluator

New evaluator plugin registered as `("evaluator", "bpb")`:

- Runs model on evaluation data, computes per-token cross-entropy loss
- Converts nats to bits (divide by ln(2))
- Divides by total byte count of input text
- Returns `{"val_bpb": float, "val_loss": float}`

BPB is vocab-size independent — fairly compares across different base models with different tokenizers.

### 5. ExperimentTracker & Results

```python
@dataclass
class ExperimentResult:
    experiment_id: str
    parent_id: str | None
    description: str
    config_snapshot: dict[str, Any]
    val_bpb: float | None
    val_loss: float | None
    domain_score: float | None
    training_time_s: float
    total_steps: int
    final_loss: float
    status: str                        # "improved", "regressed", "failed", "baseline"
    reasoning: str
    timestamp: str
```

**Decision logic:**

| Outcome | Action |
|---|---|
| val_bpb improved (lower) | Keep as new best, agent builds on this |
| val_bpb regressed | Revert to previous best config, log as "regressed" |
| Training crashed/failed | Revert, log as "failed", agent sees error message |
| Timeout exceeded | Use partial results if eval was reached, else mark "failed" |

**Storage:**
- `output/research/experiments.tsv` — append-only log of all experiments
- `output/research/best_config.yaml` — current best config
- `output/research/best_model/` — saved weights from best experiment

**Events:** `experiment_start`, `experiment_complete`, `experiment_improved`, `experiment_reverted`, `research_complete`

### 6. CLI Commands

```
adaptron research                              # interactive - uses adaptron.yaml
adaptron research --time-budget 300            # 5 min per experiment
adaptron research --max-experiments 100        # run 100 experiments
adaptron research --trainer qlora              # use specific trainer
adaptron research --mode hybrid               # allow code modifications
adaptron research --strategy explore_exploit   # search strategy
adaptron research --resume output/research/    # resume from previous run
```

### 7. API Routes

```
POST /api/research/start          # start autonomous research session
GET  /api/research/status         # current experiment progress
GET  /api/research/results        # all experiment results
POST /api/research/stop           # gracefully stop after current experiment
GET  /api/research/best           # best result so far
```

### 8. File Layout

```
adaptron/research/
├── __init__.py
├── config.py          # ResearchConfig, ExperimentProposal dataclasses
├── runner.py          # ExperimentRunner - main orchestrator loop
├── agent.py           # ExperimentAgent - LLM-driven proposal generation
├── tracker.py         # ExperimentTracker - TSV logging, best tracking
├── timer.py           # TimeBudgetWrapper - wall-clock training cutoff

adaptron/evaluate/
├── bpb.py             # BPBEvaluator plugin

adaptron/cli/main.py          # + research command
adaptron/api/routes/research.py   # Research API routes
adaptron/api/main.py              # + research router

tests/research/
├── test_config.py, test_agent.py, test_tracker.py, test_timer.py, test_runner.py
tests/evaluate/test_bpb.py
```

## Dependencies

No new dependencies required. Agent calls use whatever LLM API is configured. BPB evaluation uses only PyTorch. Time-budget wrapper is pure Python.

## Error Handling

- Agent proposal validation: reject invalid fields, out-of-range values, syntax errors in code
- Training failures: catch exceptions, log as "failed", revert to last good config, continue loop
- LLM API failures: retry with exponential backoff (3 attempts), skip experiment on persistent failure
- Time budget enforcement: graceful signal to stop training, save partial checkpoint if possible
- Resume support: tracker reads existing TSV to reconstruct state after interruption
