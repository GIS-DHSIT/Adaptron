from adaptron.research.config import ResearchConfig, ExperimentProposal, ExperimentResult
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
