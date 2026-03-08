from adaptron.validate.config import ValidationConfig
from adaptron.validate.engine import ValidationEngine
from adaptron.core.events import EventBus, Event


def test_full_validation_pipeline(tmp_path):
    """E2E: run all validators, generate reports, check grade."""
    config = ValidationConfig(
        model_path=str(tmp_path / "model"),
        output_dir=str(tmp_path / "reports"),
    )

    bus = EventBus()
    events: list[Event] = []
    bus.on("*", lambda e: events.append(e))

    engine = ValidationEngine(config=config, event_bus=bus)

    predictions = ["Paris", "Berlin", "Tokyo", "London", "Rome"]
    references = ["Paris", "Berlin", "Tokyo", "Madrid", "Rome"]
    prompts = [f"Question {i}" for i in range(5)]

    report = engine.validate(
        predictions=predictions,
        references=references,
        prompts=prompts,
        baseline_preds=["Paris", "wrong", "Tokyo", "wrong", "wrong"],
        latency_durations_ms=[100, 110, 95, 105, 200, 150, 130, 120, 115, 180,
                              100, 110, 95, 105, 200, 150, 130, 120, 115, 180],
        responses_per_prompt=[
            ["Paris", "Paris", "Paris"],
            ["Berlin", "Berlin", "Berlin"],
            ["Tokyo", "Tokyo", "Tokyo"],
        ],
        model_info={"name": "test-model", "base_model": "base", "training_mode": "qlora"},
    )

    assert report.overall_grade in ("A", "B", "C", "D", "F")
    assert report.benchmark is not None
    assert report.benchmark.metrics["exact_match"] == 0.8
    assert report.comparison is not None
    assert report.comparison.wins > 0
    assert report.readiness is not None
    assert report.hallucination is not None
    assert len(report.summary) > 0

    from pathlib import Path
    assert (Path(tmp_path / "reports" / "report.json")).exists()
    assert (Path(tmp_path / "reports" / "report.html")).exists()

    event_types = [e.type for e in events]
    assert "validation.started" in event_types
    assert "validation.completed" in event_types
    assert "validation.report.completed" in event_types
