"""Pipeline factory that assembles stages from a PipelineConfig."""

from __future__ import annotations

from adaptron.core.config import PipelineConfig
from adaptron.core.events import EventBus
from adaptron.core.pipeline import PipelineOrchestrator, StageResult, StageStatus
from adaptron.core.registry import global_registry
from adaptron.understand.models import Chunk


class IngestStage:
    """Ingest stage that processes all configured data sources."""
    name = "ingest"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        # Import to trigger plugin registration
        import adaptron.ingest.pdf
        import adaptron.ingest.sql

        documents = []
        # For now, store empty docs - actual ingestion requires real data sources
        context["documents"] = documents
        return StageResult(status=StageStatus.COMPLETED, output={"document_count": len(documents)})


class UnderstandStage:
    """Understand stage that chunks, extracts entities, and scores quality."""
    name = "understand"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        from adaptron.understand.chunker import SemanticChunker
        from adaptron.understand.entities import RegexEntityExtractor
        from adaptron.understand.quality import QualityScorer

        documents = context.get("documents", [])
        chunker = SemanticChunker()
        all_chunks = []
        for doc in documents:
            all_chunks.extend(chunker.chunk(doc))

        extractor = RegexEntityExtractor()
        all_entities = []
        for chunk in all_chunks:
            all_entities.extend(extractor.extract(chunk.content))

        scorer = QualityScorer()
        quality = scorer.score(all_chunks)

        context["chunks"] = all_chunks
        context["entities"] = all_entities
        context["quality"] = quality
        return StageResult(status=StageStatus.COMPLETED, output={"chunk_count": len(all_chunks), "entity_count": len(all_entities), "quality_score": quality.overall})


class SynthesizeStage:
    """Synthesize stage that generates training data from chunks."""
    name = "synthesize"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        from adaptron.synthesize.instruction import TemplateInstructionGenerator

        chunks = context.get("chunks", [])
        generator = TemplateInstructionGenerator()
        dataset = generator.generate(chunks)
        context["dataset"] = dataset
        return StageResult(status=StageStatus.COMPLETED, output={"dataset_size": len(dataset)})


class PipelineFactory:
    """Assembles pipeline stages from a PipelineConfig."""

    @staticmethod
    def create(config: PipelineConfig, bus: EventBus | None = None) -> PipelineOrchestrator:
        bus = bus or EventBus()
        pipeline = PipelineOrchestrator(bus=bus)

        pipeline.add_stage("ingest", IngestStage(config))
        pipeline.add_stage("understand", UnderstandStage(config))
        pipeline.add_stage("synthesize", SynthesizeStage(config))

        return pipeline
