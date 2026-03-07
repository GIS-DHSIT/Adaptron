"""Tests for pipeline configuration dataclasses."""

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
