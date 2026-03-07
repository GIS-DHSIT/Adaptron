import pytest
from adaptron.core.pipeline import PipelineOrchestrator, StageResult, StageStatus
from adaptron.core.events import EventBus


class FakeStage:
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.executed = False

    async def run(self, context: dict) -> StageResult:
        self.executed = True
        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")
        context[self.name] = "done"
        return StageResult(status=StageStatus.COMPLETED, output={"result": "ok"})


@pytest.mark.asyncio
async def test_pipeline_runs_stages_in_order():
    bus = EventBus()
    pipeline = PipelineOrchestrator(bus=bus)
    s1 = FakeStage("ingest")
    s2 = FakeStage("understand")
    pipeline.add_stage("ingest", s1)
    pipeline.add_stage("understand", s2)
    result = await pipeline.execute({})
    assert s1.executed
    assert s2.executed
    assert result.status == StageStatus.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_stops_on_failure():
    bus = EventBus()
    pipeline = PipelineOrchestrator(bus=bus)
    s1 = FakeStage("ingest", should_fail=True)
    s2 = FakeStage("understand")
    pipeline.add_stage("ingest", s1)
    pipeline.add_stage("understand", s2)
    result = await pipeline.execute({})
    assert s1.executed
    assert not s2.executed
    assert result.status == StageStatus.FAILED


@pytest.mark.asyncio
async def test_pipeline_emits_events():
    bus = EventBus()
    events = []
    bus.on("*", lambda e: events.append(e.type))
    pipeline = PipelineOrchestrator(bus=bus)
    pipeline.add_stage("ingest", FakeStage("ingest"))
    await pipeline.execute({})
    assert "stage_start" in events
    assert "stage_complete" in events
    assert "pipeline_complete" in events
