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


@router.post("/stop")
def research_stop():
    global _active_runner
    if _active_runner is None:
        return {"status": "no active session"}
    _active_runner = None
    return {"status": "stopped"}
