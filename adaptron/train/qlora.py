from __future__ import annotations

import logging
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.core.registry import register_plugin
from adaptron.train.base import BaseTrainer
from adaptron.train.models import TrainConfig, TrainResult

logger = logging.getLogger(__name__)


@register_plugin("trainer", "qlora")
class QLoRATrainer(BaseTrainer):
    def _build_lora_config(self, config: TrainConfig) -> dict[str, Any]:
        return {
            "r": config.lora_rank,
            "lora_alpha": config.lora_alpha,
            "lora_dropout": config.lora_dropout,
            "target_modules": config.target_modules,
            "bias": "none",
            "task_type": "CAUSAL_LM",
        }

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
                data={"mode": "qlora", "base_model": config.base_model},
            ),
        )
        try:
            return await self._train_with_unsloth(config, dataset, bus)
        except ImportError:
            logger.info("Unsloth not available, falling back to HuggingFace PEFT")
            return await self._train_with_peft(config, dataset, bus)

    async def _train_with_unsloth(
        self,
        config: TrainConfig,
        dataset: list[dict[str, Any]],
        bus: EventBus,
    ) -> TrainResult:
        from unsloth import FastLanguageModel  # type: ignore[import-untyped]
        from trl import SFTTrainer  # type: ignore[import-untyped]
        from transformers import TrainingArguments  # type: ignore[import-untyped]
        from datasets import Dataset  # type: ignore[import-untyped]

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=config.base_model,
            max_seq_length=config.max_seq_length,
            load_in_4bit=config.use_4bit,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=config.lora_rank,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            target_modules=config.target_modules,
        )

        hf_dataset = Dataset.from_list(dataset)

        def formatting_func(examples):
            return [
                f"### Instruction:\n{i}\n\n### Response:\n{r}"
                for i, r in zip(examples["instruction"], examples["response"])
            ]

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

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=hf_dataset,
            formatting_func=formatting_func,
            args=training_args,
            max_seq_length=config.max_seq_length,
        )

        train_result = trainer.train()
        model.save_pretrained(config.output_dir)
        tokenizer.save_pretrained(config.output_dir)

        bus.emit(
            "train_complete",
            Event(
                type="train_complete",
                data={"mode": "qlora", "loss": train_result.training_loss},
            ),
        )

        return TrainResult(
            model_path=config.output_dir,
            adapter_path=config.output_dir,
            training_mode="qlora",
            base_model=config.base_model,
            total_steps=train_result.global_step,
            final_loss=train_result.training_loss,
            metrics={"training_loss": train_result.training_loss},
        )

    async def _train_with_peft(
        self,
        config: TrainConfig,
        dataset: list[dict[str, Any]],
        bus: EventBus,
    ) -> TrainResult:
        from transformers import (  # type: ignore[import-untyped]
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            BitsAndBytesConfig,
        )
        from peft import (  # type: ignore[import-untyped]
            LoraConfig,
            get_peft_model,
            prepare_model_for_kbit_training,
        )
        from trl import SFTTrainer  # type: ignore[import-untyped]
        from datasets import Dataset  # type: ignore[import-untyped]
        import torch

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        model = AutoModelForCausalLM.from_pretrained(
            config.base_model,
            quantization_config=bnb_config,
            device_map="auto",
        )
        tokenizer = AutoTokenizer.from_pretrained(config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = prepare_model_for_kbit_training(model)
        lora_config = LoraConfig(**self._build_lora_config(config))
        model = get_peft_model(model, lora_config)

        hf_dataset = Dataset.from_list(dataset)

        def formatting_func(examples):
            return [
                f"### Instruction:\n{i}\n\n### Response:\n{r}"
                for i, r in zip(examples["instruction"], examples["response"])
            ]

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

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=hf_dataset,
            formatting_func=formatting_func,
            args=training_args,
            max_seq_length=config.max_seq_length,
        )

        train_result = trainer.train()
        model.save_pretrained(config.output_dir)
        tokenizer.save_pretrained(config.output_dir)

        bus.emit(
            "train_complete",
            Event(
                type="train_complete",
                data={"mode": "qlora-peft", "loss": train_result.training_loss},
            ),
        )

        return TrainResult(
            model_path=config.output_dir,
            adapter_path=config.output_dir,
            training_mode="qlora",
            base_model=config.base_model,
            total_steps=train_result.global_step,
            final_loss=train_result.training_loss,
            metrics={"training_loss": train_result.training_loss},
        )
