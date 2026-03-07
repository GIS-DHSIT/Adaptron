from adaptron.train.base import BaseTrainer
from adaptron.train.models import TrainConfig, TrainResult


def test_train_config_defaults():
    config = TrainConfig(base_model="test/model", output_dir="/tmp/out")
    assert config.epochs == 3
    assert config.learning_rate == 2e-4


def test_base_trainer_is_abstract():
    try:
        BaseTrainer()
        assert False
    except TypeError:
        pass
