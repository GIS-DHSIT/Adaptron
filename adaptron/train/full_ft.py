from __future__ import annotations

import logging
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.core.registry import register_plugin
from adaptron.train.base import BaseTrainer
from adaptron.train.models import TrainConfig, TrainResult

logger = logging.getLogger(__name__)


@register_plugin("trainer", "full_ft")
class FullFTTrainer(BaseTrainer):
    async def train(
        self,
        config: TrainConfig,
        dataset: list[dict[str, Any]],
        event_bus: EventBus | None = None,
    ) -> TrainResult:
        bus = event_bus or EventBus()
        bus.emit(
            "train_start",
            Event(
                type="train_start",
                data={"mode": "full_ft", "base_model": config.base_model},
            ),
        )

        try:
            from transformers import (  # type: ignore[import-untyped]
                AutoModelForCausalLM,
                AutoTokenizer,
                Trainer,
                TrainingArguments,
            )
            from datasets import Dataset  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Full fine-tuning requires 'transformers' and 'datasets'. "
                "Install them with: pip install transformers datasets"
            ) from exc

        model = AutoModelForCausalLM.from_pretrained(
            config.base_model,
            device_map="auto",
        )
        tokenizer = AutoTokenizer.from_pretrained(config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # All parameters are unfrozen for full fine-tuning (default)
        for param in model.parameters():
            param.requires_grad = True

        hf_dataset = Dataset.from_list(dataset)

        def tokenize_fn(examples):
            texts = [
                f"### Instruction:\n{i}\n\n### Response:\n{r}"
                for i, r in zip(examples["instruction"], examples["response"])
            ]
            return tokenizer(
                texts,
                truncation=True,
                max_length=config.max_seq_length,
                padding="max_length",
            )

        hf_dataset = hf_dataset.map(tokenize_fn, batched=True)

        training_args = TrainingArguments(
            output_dir=config.output_dir,
            num_train_epochs=config.epochs,
            per_device_train_batch_size=config.batch_size,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            learning_rate=config.learning_rate,
            warmup_ratio=config.warmup_ratio,
            weight_decay=config.weight_decay,
            logging_steps=10,
            save_strategy="epoch",
            fp16=True,
        )

        trainer = Trainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=hf_dataset,
            args=training_args,
        )

        train_result = trainer.train()
        model.save_pretrained(config.output_dir)
        tokenizer.save_pretrained(config.output_dir)

        bus.emit(
            "train_complete",
            Event(
                type="train_complete",
                data={"mode": "full_ft", "loss": train_result.training_loss},
            ),
        )

        return TrainResult(
            model_path=config.output_dir,
            adapter_path=None,
            training_mode="full_ft",
            base_model=config.base_model,
            total_steps=train_result.global_step,
            final_loss=train_result.training_loss,
            metrics={"training_loss": train_result.training_loss},
        )
