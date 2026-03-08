from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/validate", tags=["validate"])

_active_report = None

@router.get("/status")
def validate_status():
    if _active_report is None:
        return {"running": False, "message": "No validation in progress"}
    return {"running": False, "grade": _active_report.overall_grade}

@router.get("/report")
def validate_report():
    if _active_report is None:
        return {"report": None}
    from dataclasses import asdict
    return {"report": asdict(_active_report)}

@router.post("/start")
async def validate_start(body: dict | None = None):
    return {"status": "accepted", "message": "Validation requires model path. Use CLI for full validation."}
