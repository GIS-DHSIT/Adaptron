"""Experiment agent that proposes config changes via LLM."""

from __future__ import annotations

import copy
import json
import logging
import os
import uuid
from dataclasses import asdict, fields
from typing import Any

from adaptron.research.config import ExperimentProposal, ExperimentResult, ResearchConfig
from adaptron.train.models import TrainConfig

logger = logging.getLogger(__name__)

VALID_CONFIG_FIELDS = {f.name for f in fields(TrainConfig)}
NUMERIC_POSITIVE_FIELDS = {
    "learning_rate",
    "batch_size",
    "epochs",
    "lora_rank",
    "lora_alpha",
    "max_seq_length",
    "gradient_accumulation_steps",
}


class ExperimentAgent:
    """Agent that validates proposals, applies config changes, and calls an LLM."""

    def __init__(self, config: ResearchConfig) -> None:
        self.config = config

    def validate_proposal(self, changes: dict[str, Any]) -> list[str]:
        """Validate proposed config changes. Returns list of error strings (empty = valid)."""
        errors: list[str] = []
        for key, value in changes.items():
            if key not in VALID_CONFIG_FIELDS:
                errors.append(f"Unknown config field: {key}")
                continue
            if key in NUMERIC_POSITIVE_FIELDS:
                if not isinstance(value, (int, float)) or value <= 0:
                    errors.append(
                        f"Field '{key}' must be a positive number, got {value!r}"
                    )
        return errors

    def apply_changes(
        self, base_config: TrainConfig, changes: dict[str, Any]
    ) -> TrainConfig:
        """Return a deep copy of base_config with the given changes applied."""
        config_dict = asdict(base_config)
        config_dict.update(changes)
        return TrainConfig(**config_dict)

    def build_prompt(
        self,
        current_config: TrainConfig,
        history: list[ExperimentResult],
    ) -> str:
        """Build the LLM prompt string from current config and experiment history."""
        config_dict = asdict(current_config)
        config_lines = json.dumps(config_dict, indent=2)

        history_lines = []
        for result in history:
            entry = (
                f"  - {result.experiment_id}: status={result.status}, "
                f"val_bpb={result.val_bpb}, final_loss={result.final_loss}, "
                f"config_snapshot={json.dumps(result.config_snapshot)}"
            )
            history_lines.append(entry)
        history_text = "\n".join(history_lines) if history_lines else "  (none)"

        valid_fields = ", ".join(sorted(VALID_CONFIG_FIELDS))

        prompt = f"""You are an autonomous research agent optimizing LLM fine-tuning hyperparameters.

Current config:
{config_lines}

Experiment history:
{history_text}

Valid config fields: {valid_fields}

Based on the experiment history, propose ONE config change that is likely to improve validation BPB (bits per byte). Lower is better.

Respond with a JSON object:
{{
  "experiment_id": "exp-<short-id>",
  "description": "<brief description>",
  "config_changes": {{"field_name": new_value, ...}},
  "reasoning": "<why this change should help>"
}}"""
        return prompt

    async def propose(
        self,
        current_config: TrainConfig,
        history: list[ExperimentResult],
    ) -> ExperimentProposal:
        """Call LLM to get a new experiment proposal."""
        prompt = self.build_prompt(current_config, history)
        response_text = await self._call_llm(prompt)

        try:
            data = json.loads(response_text)
            return ExperimentProposal(
                experiment_id=data.get("experiment_id", f"exp-{uuid.uuid4().hex[:8]}"),
                description=data.get("description", "LLM-proposed experiment"),
                config_changes=data.get("config_changes", {}),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse LLM response: %s", exc)
            return self._fallback_proposal()

    async def _call_llm(self, prompt: str) -> str:
        """Call Anthropic API. Falls back to a default proposal if no API key."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.info("No ANTHROPIC_API_KEY set, using fallback proposal")
            return json.dumps(self._fallback_proposal_dict())

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.config.agent_model,
                        "max_tokens": 1024,
                        "temperature": 0,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except Exception as exc:
            logger.warning("LLM API call failed: %s, using fallback", exc)
            return json.dumps(self._fallback_proposal_dict())

    def _fallback_proposal_dict(self) -> dict[str, Any]:
        """Generate a fallback proposal dictionary."""
        return {
            "experiment_id": f"exp-{uuid.uuid4().hex[:8]}",
            "description": "Fallback: try lower learning rate",
            "config_changes": {
                "learning_rate": self.config.base_config.learning_rate * 0.5
            },
            "reasoning": "No LLM available; defaulting to halving the learning rate.",
        }

    def _fallback_proposal(self) -> ExperimentProposal:
        """Generate a fallback ExperimentProposal."""
        d = self._fallback_proposal_dict()
        return ExperimentProposal(
            experiment_id=d["experiment_id"],
            description=d["description"],
            config_changes=d["config_changes"],
            reasoning=d["reasoning"],
        )
