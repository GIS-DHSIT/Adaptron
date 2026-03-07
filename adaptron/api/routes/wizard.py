from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from adaptron.core.config import PipelineConfig, WizardAnswers

router = APIRouter(prefix="/api/wizard", tags=["wizard"])


class WizardRequest(BaseModel):
    primary_goal: str
    data_sources: list[str]
    data_freshness: str
    hardware: str
    timeline: str
    accuracy: str
    model_size: str


class WizardResponse(BaseModel):
    training_modes: list[str]
    base_model: str
    deploy_targets: list[str]


@router.post("/recommend", response_model=WizardResponse)
def recommend(req: WizardRequest):
    answers = WizardAnswers(
        primary_goal=req.primary_goal,
        data_sources=req.data_sources,
        data_freshness=req.data_freshness,
        hardware=req.hardware,
        timeline=req.timeline,
        accuracy=req.accuracy,
        model_size=req.model_size,
    )
    config = PipelineConfig.from_wizard(answers)
    return WizardResponse(
        training_modes=config.training_modes,
        base_model=config.base_model,
        deploy_targets=config.deploy_targets,
    )
