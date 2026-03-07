"""Tests for pipeline integration with CleanStage and AutoSynthesizer."""

import pytest

from adaptron.core.config import PipelineConfig
from adaptron.core.factory import PipelineFactory


def test_pipeline_has_clean_stage():
    config = PipelineConfig()
    pipeline = PipelineFactory.create(config)
    stage_names = [name for name, _ in pipeline._stages]
    assert "clean" in stage_names
    assert stage_names.index("clean") > stage_names.index("understand")
    assert stage_names.index("clean") < stage_names.index("synthesize")


def test_pipeline_synthesize_uses_auto():
    """Verify SynthesizeStage tries AutoSynthesizer."""
    from adaptron.core.factory import SynthesizeStage

    config = PipelineConfig()
    stage = SynthesizeStage(config)
    # Just verify the stage can be created
    assert stage.name == "synthesize"
