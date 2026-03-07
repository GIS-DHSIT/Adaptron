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
        ExperimentProposal(
            experiment_id=f"exp-{i}",
            description=f"change {i}",
            config_changes={"learning_rate": 0.001 * (i + 1)},
            reasoning=f"test {i}",
        )
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
