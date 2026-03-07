from adaptron.train.qlora import QLoRATrainer
from adaptron.train.models import TrainConfig


def test_qlora_trainer_builds_config():
    trainer = QLoRATrainer()
    config = TrainConfig(
        base_model="test/model",
        output_dir="/tmp/out",
        training_mode="qlora",
        lora_rank=32,
        lora_alpha=64,
    )
    lora_config = trainer._build_lora_config(config)
    assert lora_config["r"] == 32
    assert lora_config["lora_alpha"] == 64


def test_qlora_trainer_registered():
    from adaptron.core.registry import global_registry

    plugin = global_registry.get("trainer", "qlora")
    assert plugin is QLoRATrainer
