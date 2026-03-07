import pytest
from unittest.mock import AsyncMock

from adaptron.research.runner import ExperimentRunner
from adaptron.research.config import ResearchConfig, ExperimentProposal
from adaptron.train.models import TrainConfig, TrainResult
from adaptron.core.events import EventBus


def _make_research_config(tmp_path):
    return ResearchConfig(
        base_config=TrainConfig(
            base_model="test/model", output_dir=str(tmp_path / "output")
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
