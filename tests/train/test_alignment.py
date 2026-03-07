import pytest
from unittest.mock import MagicMock, patch

from adaptron.train.alignment import DPOAlignmentTrainer
from adaptron.train.models import TrainConfig


def test_registered_as_trainer_dpo():
    from adaptron.core.registry import global_registry

    plugin = global_registry.get("trainer", "dpo")
    assert plugin is DPOAlignmentTrainer


@pytest.mark.asyncio
async def test_dpo_train_mocked():
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    mock_tokenizer.pad_token = None
    mock_tokenizer.eos_token = "<eos>"

    mock_train_result = MagicMock()
    mock_train_result.training_loss = 0.6
    mock_train_result.global_step = 80

    mock_trainer_instance = MagicMock()
    mock_trainer_instance.train.return_value = mock_train_result

    mock_dataset = MagicMock()

    mock_transformers = MagicMock()
    mock_transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
    mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    mock_transformers.TrainingArguments.return_value = MagicMock()

    mock_datasets = MagicMock()
    mock_datasets.Dataset.from_list.return_value = mock_dataset

    mock_trl = MagicMock()
    mock_trl.DPOTrainer.return_value = mock_trainer_instance

    import sys

    with patch.dict(sys.modules, {
        "transformers": mock_transformers,
        "datasets": mock_datasets,
        "trl": mock_trl,
    }):
        trainer = DPOAlignmentTrainer()
        config = TrainConfig(
            base_model="test/model",
            output_dir="/tmp/dpo_out",
            training_mode="dpo",
        )
        dataset = [
            {
                "prompt": "What is AI?",
                "chosen": "AI is artificial intelligence.",
                "rejected": "AI is magic.",
            },
        ]
        result = await trainer.train(config, dataset)

    assert result.training_mode == "dpo"
    assert result.model_path == "/tmp/dpo_out"
    assert result.adapter_path is None
    assert result.final_loss == 0.6
    assert result.total_steps == 80
    mock_trl.DPOTrainer.assert_called_once()
    mock_trainer_instance.train.assert_called_once()
