from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/research", tags=["research"])

# Module-level state for tracking active research
_active_runner = None


@router.get("/status")
def research_status():
    if _active_runner is None:
        return {"running": False, "message": "No active research session"}
    summary = _active_runner.tracker.summary()
    return {"running": True, **summary}


@router.get("/results")
def research_results():
    if _active_runner is None:
        return {"results": []}
    return {"results": _active_runner.tracker.list_results()}


@router.get("/best")
def research_best():
    if _active_runner is None:
        return {"best": None}
    return {"best": _active_runner.tracker.get_best()}


@router.post("/start")
async def research_start(body: dict | None = None):
    import asyncio
    from adaptron.research.config import ResearchConfig
    from adaptron.research.runner import ExperimentRunner
    from adaptron.train.models import TrainConfig

    global _active_runner
    if _active_runner is not None:
        return {"status": "already running"}

    body = body or {}
    train_config = TrainConfig(
        base_model=body.get("base_model", "unsloth/tinyllama"),
        output_dir=body.get("output_dir", "output"),
    )
    research_config = ResearchConfig(
        base_config=train_config,
        time_budget=body.get("time_budget", 300),
        max_experiments=body.get("max_experiments", 50),
        trainer_plugin=body.get("trainer", "qlora"),
        mode=body.get("mode", "config"),
        strategy=body.get("strategy", "explore_exploit"),
    )
    _active_runner = ExperimentRunner(
        config=research_config,
        output_dir=body.get("output_dir", "output"),
    )
    asyncio.create_task(_active_runner.run())
    return {"status": "started", "max_experiments": research_config.max_experiments}


@router.post("/stop")
def research_stop():
    global _active_runner
    if _active_runner is None:
        return {"status": "no active session"}
    _active_runner = None
    return {"status": "stopped"}
