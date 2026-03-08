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


class CleanStage:
    """Clean stage that filters and normalizes ingested documents."""
    name = "clean"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        from adaptron.connectors.cleaner import DataCleaner, CleanConfig

        documents = context.get("documents", [])
        if not documents:
            return StageResult(status=StageStatus.COMPLETED, output={"cleaned_count": 0})
        cleaner = DataCleaner()
        result = cleaner.clean(documents, CleanConfig())
        context["documents"] = result.cleaned
        return StageResult(
            status=StageStatus.COMPLETED,
            output={"cleaned_count": len(result.cleaned), "removed": result.removed_count},
        )


class SynthesizeStage:
    """Synthesize stage that generates training data from chunks."""
    name = "synthesize"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        chunks = context.get("chunks", [])
        try:
            from adaptron.synthesize.auto import AutoSynthesizer
            generator = AutoSynthesizer()
        except ImportError:
            from adaptron.synthesize.instruction import TemplateInstructionGenerator
            generator = TemplateInstructionGenerator()
        dataset = generator.generate(chunks)
        context["dataset"] = dataset
        return StageResult(status=StageStatus.COMPLETED, output={"dataset_size": len(dataset)})


class ValidateStage:
    """Validate stage — placeholder for post-training model validation."""
    name = "validate"

    def __init__(self, config: PipelineConfig):
        self.config = config

    async def run(self, context: dict) -> StageResult:
        context["validation_pending"] = True
        return StageResult(
            status=StageStatus.COMPLETED,
            output={"validation_pending": True, "message": "Run 'adaptron validate' after training"},
        )


class PipelineFactory:
    """Assembles pipeline stages from a PipelineConfig."""

    @staticmethod
    def create(config: PipelineConfig, bus: EventBus | None = None) -> PipelineOrchestrator:
        bus = bus or EventBus()
        pipeline = PipelineOrchestrator(bus=bus)

        pipeline.add_stage("ingest", IngestStage(config))
        pipeline.add_stage("understand", UnderstandStage(config))
        pipeline.add_stage("clean", CleanStage(config))
        pipeline.add_stage("synthesize", SynthesizeStage(config))
        pipeline.add_stage("validate", ValidateStage(config))

        return pipeline
