from adaptron.research.agent import ExperimentAgent
from adaptron.research.config import ResearchConfig, ExperimentResult
from adaptron.train.models import TrainConfig


def _make_research_config():
    return ResearchConfig(
        base_config=TrainConfig(base_model="test/model", output_dir="/tmp/out")
    )


def _make_result(exp_id, val_bpb, status):
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
    assert base.learning_rate == 0.0002  # original unchanged


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
