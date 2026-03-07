"""End-to-end integration tests for the full pipeline."""

from __future__ import annotations

import pytest

from adaptron.core.config import PipelineConfig, WizardAnswers
from adaptron.core.events import Event, EventBus
from adaptron.core.factory import PipelineFactory, UnderstandStage, SynthesizeStage
from adaptron.core.pipeline import PipelineOrchestrator, StageStatus
from adaptron.ingest.models import RawDocument


def _make_config() -> PipelineConfig:
    answers = WizardAnswers(
        primary_goal="qa_docs",
        data_sources=["docs"],
        data_freshness="static",
        hardware="mid",
        timeline="medium",
        accuracy="professional",
        model_size="small",
    )
    return PipelineConfig.from_wizard(answers)


def _make_sample_documents() -> list[RawDocument]:
    return [
        RawDocument(
            content=(
                "Machine learning is a subset of artificial intelligence. "
                "It uses algorithms to learn from data. "
                "Neural networks are a key component of deep learning."
            ),
            metadata={"source": "test"},
            source_ref="test.txt",
        ),
        RawDocument(
            content=(
                "Contact us at info@example.com or call 555-1234. "
                "Our services cost $99.99 per month."
            ),
            metadata={"source": "test2"},
            source_ref="test2.txt",
        ),
    ]


class TestPipelineFactory:
    def test_pipeline_factory_creates_pipeline(self):
        config = _make_config()
        bus = EventBus()
        pipeline = PipelineFactory.create(config, bus=bus)

        assert isinstance(pipeline, PipelineOrchestrator)
        # The orchestrator stores stages as a list of (name, stage) tuples
        assert len(pipeline._stages) == 3
        names = [name for name, _ in pipeline._stages]
        assert names == ["ingest", "understand", "synthesize"]


class TestPipelineE2E:
    @pytest.mark.asyncio
    async def test_pipeline_e2e_with_preloaded_documents(self):
        config = _make_config()
        bus = EventBus()
        events_received: list[Event] = []
        bus.on("*", lambda e: events_received.append(e))

        # Build pipeline with only understand + synthesize stages so that
        # IngestStage does not overwrite the pre-loaded documents.
        pipeline = PipelineOrchestrator(bus=bus)
        pipeline.add_stage("understand", UnderstandStage(config))
        pipeline.add_stage("synthesize", SynthesizeStage(config))

        # Pre-load documents into context, bypassing IngestStage's empty result
        docs = _make_sample_documents()
        context: dict = {"documents": docs}

        result = await pipeline.execute(context)

        # Pipeline completes successfully
        assert result.status == StageStatus.COMPLETED

        # Context has chunks, entities, quality, dataset
        assert "chunks" in context
        assert "entities" in context
        assert "quality" in context
        assert "dataset" in context

        # Chunks were created from the documents
        assert len(context["chunks"]) > 0
        # Each document should produce at least one chunk
        source_refs = {c.source_ref for c in context["chunks"]}
        assert "test.txt" in source_refs
        assert "test2.txt" in source_refs

        # Dataset was generated from chunks
        assert len(context["dataset"]) > 0
        assert len(context["dataset"]) == len(context["chunks"])
        for item in context["dataset"]:
            assert "instruction" in item
            assert "response" in item

        # Events were emitted
        assert len(events_received) > 0
        event_types = [e.type for e in events_received]
        assert "pipeline_start" in event_types
        assert "pipeline_complete" in event_types

    @pytest.mark.asyncio
    async def test_pipeline_e2e_empty_data(self):
        config = _make_config()
        pipeline = PipelineFactory.create(config)

        result = await pipeline.execute()

        # Pipeline should complete without errors even with no data
        assert result.status == StageStatus.COMPLETED

        # All three stages should have completed
        assert len(result.stage_results) == 3
        for name, sr in result.stage_results.items():
            assert sr.status == StageStatus.COMPLETED, f"Stage '{name}' did not complete"


class TestPipelineEvents:
    @pytest.mark.asyncio
    async def test_pipeline_events_are_emitted(self):
        config = _make_config()
        bus = EventBus()
        events_received: list[Event] = []
        bus.on("*", lambda e: events_received.append(e))

        pipeline = PipelineFactory.create(config, bus=bus)
        docs = _make_sample_documents()
        context: dict = {"documents": docs}

        await pipeline.execute(context)

        event_types = [e.type for e in events_received]

        # Verify expected event types are present
        assert "pipeline_start" in event_types
        assert "pipeline_complete" in event_types
        assert event_types.count("stage_start") == 3
        assert event_types.count("stage_complete") == 3

        # Verify ordering: pipeline_start first, pipeline_complete last
        assert event_types[0] == "pipeline_start"
        assert event_types[-1] == "pipeline_complete"

        # Verify stage events appear in correct order (start before complete for each)
        expected_order = [
            "pipeline_start",
            "stage_start", "stage_complete",   # ingest
            "stage_start", "stage_complete",   # understand
            "stage_start", "stage_complete",   # synthesize
            "pipeline_complete",
        ]
        assert event_types == expected_order

        # Verify stage names in stage events
        stage_starts = [e for e in events_received if e.type == "stage_start"]
        stage_names = [e.data["stage"] for e in stage_starts]
        assert stage_names == ["ingest", "understand", "synthesize"]
