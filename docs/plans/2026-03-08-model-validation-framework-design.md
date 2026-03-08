# Model Validation Framework Design

**Date:** 2026-03-08
**Status:** Approved

## Overview

A Model Validation Framework (MVF) that proves finetuned models are fit for purpose before deployment. A shared `ValidationEngine` runs four validators (benchmark suite, model comparator, production readiness, hallucination detector), generates dual-format reports (HTML + JSON), and is accessible via pipeline stage, CLI, and API.

## Architecture

```
adaptron validate --model ./output --test-data ./test.jsonl

                    ┌─────────────────────────────────┐
                    │      ValidationEngine            │
                    │                                  │
                    │  ┌───────────┐  ┌─────────────┐ │
                    │  │ Benchmark │  │ Comparator   │ │
                    │  │ Suite     │  │ (base vs ft) │ │
                    │  └───────────┘  └─────────────┘ │
                    │  ┌───────────┐  ┌─────────────┐ │
                    │  │ Production│  │ Hallucination│ │
                    │  │ Readiness │  │ Detector     │ │
                    │  └───────────┘  └─────────────┘ │
                    │                                  │
                    │  ┌──────────────────────────────┐│
                    │  │    ReportGenerator           ││
                    │  │    (HTML + JSON)              ││
                    │  └──────────────────────────────┘│
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ValidateStage     CLI command      API route
        (pipeline)        (standalone)     (POST /api/validate)
```

## Components

### 1. Benchmark Suite

Runs the finetuned model against a held-out test set with task-specific metrics.

**Metrics by task type:**

| Task Type | Metrics |
|---|---|
| QA / Instruction | Exact Match, F1, BLEU |
| Text Generation | ROUGE-1, ROUGE-L, BPB |
| Classification | Accuracy, Precision, Recall, F1 |
| Chat / Dialogue | Response relevance (cosine similarity), coherence |

**Workflow:**
1. Loads test data from JSONL (instruction/response pairs)
2. Auto-detects task type from data shape, or user specifies explicitly
3. Runs batched inference on all test samples
4. Computes metrics, returns per-sample and aggregate scores
5. Each metric graded: Pass / Warning / Fail based on configurable thresholds

**Test data sourcing:** If no explicit test data provided, automatically holds out 10% of training data (configurable via `test_split_ratio`).

### 2. Model Comparator

Runs the same prompts through finetuned model and a baseline, quantifies improvement.

**Baselines supported:**
- Base model (pre-finetune) — default
- Any Ollama or HuggingFace model user specifies
- Ground-truth reference answers

**Outputs:**
- Side-by-side response table (prompt → base → finetuned → reference)
- Aggregate improvement: percentage change in each metric vs baseline
- Win/loss/tie breakdown per prompt
- Latency comparison: tokens/second for both models

**Sampling:** Configurable subset (default 50 samples). Same prompts for both models.

Uses existing `PlaygroundEngine.compare()` for Ollama, adds direct HuggingFace inference path for non-deployed models.

### 3. Production Readiness Checks

Non-functional checks for safety and performance. Advisory only (no hard gates).

| Check | Description |
|---|---|
| Latency benchmark | tokens/sec, time-to-first-token, p50/p95/p99 across 20 runs |
| Consistency | Same 10 prompts 3x each, flag variance beyond 0.85 cosine similarity |
| Edge cases | Empty input, very long input (2x max_seq_length), special chars, multi-language, adversarial |
| Refusal detection | Legitimate prompts not refused, harmful prompts not answered |
| Output format | JSON when asked for JSON, lists when asked for lists |
| Memory footprint | GPU/CPU memory usage during inference |

Each check returns status (pass/warning/fail) and details.

### 4. Hallucination Detector

Dual strategy based on data availability.

**Reference-based (when ground truth exists):**
- Compares output against reference using token overlap + semantic similarity
- Decomposes output into atomic claims, checks each against reference
- Reports `faithfulness_score` (0-1): ratio of supported to total claims

**Self-consistency (no ground truth):**
- Runs each prompt 5 times with temperature > 0
- Computes pairwise similarity between responses
- Flags divergent responses (similarity < 0.7)
- Reports `consistency_score` (0-1): average pairwise similarity

**Mode selection:** Automatic. Reference-based when test data has answers, self-consistency otherwise. Can run both simultaneously.

### 5. Report Generator & Data Models

**ValidationReport structure:**
```
ValidationReport
├── model_info: {name, base_model, training_mode, params}
├── benchmark: BenchmarkResult
├── comparison: ComparisonResult
├── readiness: ReadinessResult
├── hallucination: HallucinationResult
├── overall_grade: str (A/B/C/D/F)
├── summary: str (human-readable verdict)
└── timestamp: str
```

**Grading:**
- A: All pass, hallucination < 5%, improvement > 20%
- B: All pass/warn, hallucination < 10%
- C: Some warnings, hallucination < 20%
- D: Some failures, hallucination < 30%
- F: Critical failures or hallucination >= 30%

**Outputs:**
- `output/validation/report.html` — Scorecard, expandable sections, charts, side-by-side table
- `output/validation/report.json` — Full structured data

**Events:** `validation_start`, `validation_complete`, `validation_grade`

### 6. Entry Points

**Pipeline:** `ValidateStage` runs after training, before deployment.

**CLI:**
```
adaptron validate --model ./output --test-data ./test.jsonl --baseline base-model
```

**API:**
```
POST /api/validate/start
GET  /api/validate/status
GET  /api/validate/report
```

### 7. File Layout

```
adaptron/validate/
├── __init__.py
├── config.py          # ValidationConfig, thresholds
├── engine.py          # ValidationEngine orchestrator
├── benchmark.py       # BenchmarkSuite
├── comparator.py      # ModelComparator
├── readiness.py       # ProductionReadiness
├── hallucination.py   # HallucinationDetector
├── report.py          # ReportGenerator (HTML + JSON)
├── models.py          # Result dataclasses
├── templates/
│   └── report.html    # Jinja2 template

adaptron/cli/main.py              # + validate command
adaptron/api/routes/validate.py   # Validation API routes
adaptron/api/main.py              # + validate router
adaptron/core/factory.py          # + ValidateStage

tests/validate/
├── test_config.py, test_benchmark.py, test_comparator.py,
│   test_readiness.py, test_hallucination.py, test_report.py,
│   test_engine.py
tests/cli/test_validate.py
tests/api/test_validate.py
tests/integration/test_validate_e2e.py
```

## Dependencies

No new required dependencies. Uses existing PyTorch for inference, existing sentence-transformers for similarity. Jinja2 added as optional dependency for HTML reports.

## Error Handling

- Model loading failures: report as "unable to validate", skip all validators
- Inference failures: catch per-sample, report partial results
- Missing test data: auto-split from training data, warn if no data available
- Missing baseline model: skip comparator, run other validators
- Timeout on inference: configurable per-sample timeout (default 30s), mark as failed
