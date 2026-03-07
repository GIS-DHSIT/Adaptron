import asyncio
from unittest.mock import MagicMock, patch

from adaptron.train.cpt import CPTTrainer
from adaptron.train.models import TrainConfig


def test_registered_as_trainer_cpt():
    from adaptron.core.registry import global_registry

    plugin = global_registry.get("trainer", "cpt")
    assert plugin is CPTTrainer


def test_cpt_train_mocked():
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    mock_tokenizer.pad_token = None
    mock_tokenizer.eos_token = "<eos>"

    mock_train_result = MagicMock()
    mock_train_result.training_loss = 0.3
    mock_train_result.global_step = 200

    mock_trainer_instance = MagicMock()
    mock_trainer_instance.train.return_value = mock_train_result

    mock_dataset = MagicMock()
    mock_dataset.map.return_value = mock_dataset

    mock_transformers = MagicMock()
    mock_transformers.AutoModelForCausalLM.from_pretrained.return_value = mock_model
    mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    mock_transformers.Trainer.return_value = mock_trainer_instance
    mock_transformers.TrainingArguments.return_value = MagicMock()
    mock_transformers.DataCollatorForLanguageModeling.return_value = MagicMock()

    mock_datasets = MagicMock()
    mock_datasets.Dataset.from_list.return_value = mock_dataset

    import sys

    with patch.dict(sys.modules, {
        "transformers": mock_transformers,
        "datasets": mock_datasets,
    }):
        trainer = CPTTrainer()
        config = TrainConfig(
            base_model="test/model",
            output_dir="/tmp/cpt_out",
            training_mode="cpt",
        )
        dataset = [
            {"text": "Some raw domain text for continued pre-training."},
        ]
        result = asyncio.get_event_loop().run_until_complete(
            trainer.train(config, dataset)
        )

    assert result.training_mode == "cpt"
    assert result.model_path == "/tmp/cpt_out"
    assert result.adapter_path is None
    assert result.final_loss == 0.3
    assert result.total_steps == 200
    mock_trainer_instance.train.assert_called_once()
