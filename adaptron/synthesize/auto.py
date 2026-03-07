"""AutoSynthesizer that detects format and dispatches to the correct synthesizer."""

from __future__ import annotations

from typing import Any

from adaptron.connectors.models import DataSchema
from adaptron.core.registry import register_plugin, global_registry
from adaptron.synthesize.base import BaseSynthesizer
from adaptron.synthesize.detector import TrainingFormatDetector
from adaptron.understand.models import Chunk

# Import synthesizer modules to ensure they register themselves
import adaptron.synthesize.instruction  # noqa: F401
import adaptron.synthesize.qa  # noqa: F401
import adaptron.synthesize.chat  # noqa: F401
import adaptron.synthesize.dpo  # noqa: F401
import adaptron.synthesize.text2sql  # noqa: F401
import adaptron.synthesize.corpus  # noqa: F401


@register_plugin("synthesizer", "auto")
class AutoSynthesizer(BaseSynthesizer):
    """Automatically detects training format and dispatches to the appropriate synthesizer."""

    def __init__(self, schema: DataSchema | None = None) -> None:
        self.schema = schema
        self._detector = TrainingFormatDetector()

    def generate(self, chunks: list[Chunk]) -> list[dict[str, Any]]:
        """Detect format from schema and dispatch to the correct synthesizer."""
        format_name = self._resolve_format()
        synthesizer = self._get_synthesizer(format_name)
        return synthesizer.generate(chunks)

    def _resolve_format(self) -> str:
        """Determine the target format based on schema detection."""
        if self.schema is not None:
            recommendation = self._detector.detect(self.schema, [])
            if recommendation.confidence >= 0.4:
                return recommendation.primary_format
        return "instruction"

    def _get_synthesizer(self, format_name: str) -> BaseSynthesizer:
        """Look up the synthesizer plugin from the registry."""
        try:
            cls = global_registry.get("synthesizer", format_name)
            return cls()
        except KeyError:
            # Fall back to instruction synthesizer
            cls = global_registry.get("synthesizer", "instruction")
            return cls()
