from __future__ import annotations

import logging
from typing import Any

from adaptron.core.events import Event, EventBus
from adaptron.core.registry import register_plugin
from adaptron.train.base import BaseTrainer
from adaptron.train.models import TrainConfig, TrainResult

logger = logging.getLogger(__name__)


@register_plugin("trainer", "distill")
class DistillationTrainer(BaseTrainer):
    """Knowledge distillation trainer (teacher-student).

    Uses config.extra for distillation-specific parameters:
        - teacher_model: str - name/path of the teacher model
        - temperature: float - distillation temperature (default 2.0)
        - alpha: float - weight for soft vs hard loss (default 0.5)
    """

    async def train(
        self,
        config: TrainConfig,
        dataset: list[dict[str, Any]],
        event_bus: EventBus | None = None,
    ) -> TrainResult:
        bus = event_bus or EventBus()
        teacher_model_name = config.extra.get("teacher_model", config.base_model)
        temperature = config.extra.get("temperature", 2.0)
        alpha = config.extra.get("alpha", 0.5)

        bus.emit(
            "train_start",
            Event(
                type="train_start",
                data={
                    "mode": "distill",
                    "base_model": config.base_model,
                    "teacher_model": teacher_model_name,
                },
            ),
        )

        try:
            from transformers import (  # type: ignore[import-untyped]
                AutoModelForCausalLM,
                AutoTokenizer,
                TrainingArguments,
            )
            from datasets import Dataset  # type: ignore[import-untyped]
            import torch  # type: ignore[import-untyped]
            import torch.nn.functional as F  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Distillation training requires 'transformers', 'datasets', and "
                "'torch'. Install them with: pip install transformers datasets torch"
            ) from exc

        # Load teacher model (frozen)
        teacher = AutoModelForCausalLM.from_pretrained(
            teacher_model_name,
            device_map="auto",
        )
        teacher.eval()
        for param in teacher.parameters():
            param.requires_grad = False

        # Load student model
        student = AutoModelForCausalLM.from_pretrained(
            config.base_model,
            device_map="auto",
        )
        tokenizer = AutoTokenizer.from_pretrained(config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

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

        # Custom training loop with distillation loss
        from transformers import Trainer  # type: ignore[import-untyped]

        class DistillTrainer(Trainer):
            def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
                outputs = model(**inputs)
                student_logits = outputs.logits
                hard_loss = outputs.loss

                with torch.no_grad():
                    teacher_outputs = teacher(**inputs)
                    teacher_logits = teacher_outputs.logits

                soft_student = F.log_softmax(student_logits / temperature, dim=-1)
                soft_teacher = F.softmax(teacher_logits / temperature, dim=-1)
                kl_loss = F.kl_div(
                    soft_student, soft_teacher, reduction="batchmean"
                ) * (temperature ** 2)

                loss = alpha * kl_loss + (1.0 - alpha) * hard_loss
                return (loss, outputs) if return_outputs else loss

        trainer = DistillTrainer(
            model=student,
            tokenizer=tokenizer,
            train_dataset=hf_dataset,
            args=training_args,
        )

        train_result = trainer.train()
        student.save_pretrained(config.output_dir)
        tokenizer.save_pretrained(config.output_dir)

        bus.emit(
            "train_complete",
            Event(
                type="train_complete",
                data={"mode": "distill", "loss": train_result.training_loss},
            ),
        )

        return TrainResult(
            model_path=config.output_dir,
            adapter_path=None,
            training_mode="distill",
            base_model=config.base_model,
            total_steps=train_result.global_step,
            final_loss=train_result.training_loss,
            metrics={"training_loss": train_result.training_loss},
        )
