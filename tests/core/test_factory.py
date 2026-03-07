# tests/core/test_factory.py
import pytest
from adaptron.core.factory import PipelineFactory
from adaptron.core.config import PipelineConfig, WizardAnswers
from adaptron.core.pipeline import StageStatus


def test_factory_creates_pipeline():
    answers = WizardAnswers(
        primary_goal="qa_docs", data_sources=["docs"],
        data_freshness="static", hardware="mid",
        timeline="medium", accuracy="professional", model_size="small",
    )
    config = PipelineConfig.from_wizard(answers)
    pipeline = PipelineFactory.create(config)
    assert len(pipeline._stages) >= 3


@pytest.mark.asyncio
async def test_factory_pipeline_executes():
    answers = WizardAnswers(
        primary_goal="qa_docs", data_sources=["docs"],
        data_freshness="static", hardware="mid",
        timeline="medium", accuracy="professional", model_size="small",
    )
    config = PipelineConfig.from_wizard(answers)
    pipeline = PipelineFactory.create(config)
    result = await pipeline.execute({})
    assert result.status == StageStatus.COMPLETED
    assert "ingest" in result.stage_results
    assert "understand" in result.stage_results
    assert "synthesize" in result.stage_results
