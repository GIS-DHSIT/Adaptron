from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])
_pipelines: dict[str, dict] = {}


class PipelineStartRequest(BaseModel):
    config_path: str | None = None
    wizard_config: dict | None = None


class PipelineStatus(BaseModel):
    id: str
    status: str
    current_stage: str | None = None
    progress: float = 0.0


@router.post("/start", response_model=PipelineStatus)
def start_pipeline(req: PipelineStartRequest):
    pipeline_id = str(uuid.uuid4())[:8]
    _pipelines[pipeline_id] = {
        "status": "queued",
        "current_stage": None,
        "progress": 0.0,
    }
    return PipelineStatus(id=pipeline_id, status="queued")


@router.get("/{pipeline_id}", response_model=PipelineStatus)
def get_pipeline(pipeline_id: str):
    if pipeline_id not in _pipelines:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    p = _pipelines[pipeline_id]
    return PipelineStatus(
        id=pipeline_id,
        status=p["status"],
        current_stage=p.get("current_stage"),
        progress=p.get("progress", 0.0),
    )
