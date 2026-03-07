import pytest
from unittest.mock import MagicMock, patch

from adaptron.train.distill import DistillationTrainer
from adaptron.train.models import TrainConfig


def test_registered_as_trainer_distill():
    from adaptron.core.registry import global_registry

    plugin = global_registry.get("trainer", "distill")
    assert plugin is DistillationTrainer


@pytest.mark.asyncio
async def test_distill_train_mocked():
    mock_teacher = MagicMock()
    mock_student = MagicMock()
    mock_tokenizer = MagicMock()
    mock_tokenizer.pad_token = None
    mock_tokenizer.eos_token = "<eos>"

    mock_train_result = MagicMock()
    mock_train_result.training_loss = 0.4
    mock_train_result.global_step = 150

    mock_trainer_instance = MagicMock()
    mock_trainer_instance.train.return_value = mock_train_result

    mock_dataset = MagicMock()
    mock_dataset.map.return_value = mock_dataset

    mock_transformers = MagicMock()
    # First call returns teacher, second returns student
    mock_transformers.AutoModelForCausalLM.from_pretrained.side_effect = [
        mock_teacher, mock_student,
    ]
    mock_transformers.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
    mock_transformers.TrainingArguments.return_value = MagicMock()
    # The DistillTrainer subclass is created inside the function;
    # we mock Trainer so the subclass inherits from the mock
    mock_transformers.Trainer = type("MockTrainer", (), {
        "__init__": lambda self, **kwargs: None,
        "train": lambda self: mock_train_result,
    })

    mock_datasets = MagicMock()
    mock_datasets.Dataset.from_list.return_value = mock_dataset

    mock_torch = MagicMock()
    mock_torch_nn_functional = MagicMock()

    import sys

    with patch.dict(sys.modules, {
        "transformers": mock_transformers,
        "datasets": mock_datasets,
        "torch": mock_torch,
        "torch.nn": MagicMock(),
        "torch.nn.functional": mock_torch_nn_functional,
    }):
        trainer = DistillationTrainer()
        config = TrainConfig(
            base_model="test/student-model",
            output_dir="/tmp/distill_out",
            training_mode="distill",
            extra={
                "teacher_model": "test/teacher-model",
                "temperature": 3.0,
                "alpha": 0.7,
            },
        )
        dataset = [
            {"instruction": "Explain AI", "response": "AI is..."},
        ]
        result = await trainer.train(config, dataset)

    assert result.training_mode == "distill"
    assert result.model_path == "/tmp/distill_out"
    assert result.adapter_path is None
    assert result.final_loss == 0.4
    assert result.total_steps == 150
    # Verify teacher model was loaded
    calls = mock_transformers.AutoModelForCausalLM.from_pretrained.call_args_list
    assert calls[0][0][0] == "test/teacher-model"
    assert calls[1][0][0] == "test/student-model"
