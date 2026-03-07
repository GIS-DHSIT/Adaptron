import pytest
from pathlib import Path

from adaptron.research.tracker import ExperimentTracker
from adaptron.research.config import ExperimentResult


def _make_result(exp_id, val_bpb, status="improved"):
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
    tracker.log(_make_result("exp-1", 1.245, "baseline"))
    tracker.log(_make_result("exp-2", 1.231, "improved"))
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
