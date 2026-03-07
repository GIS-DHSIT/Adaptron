"""API routes for ingestion schedules."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("")
async def list_schedules():
    from adaptron.connectors.scheduler import IngestionScheduler

    scheduler = IngestionScheduler()
    schedules = await scheduler.list_schedules()
    return {
        "schedules": [
            {
                "schedule_id": s.schedule_id,
                "profile": s.connector_profile,
                "cron": s.cron,
                "enabled": s.enabled,
            }
            for s in schedules
        ]
    }


@router.post("")
async def create_schedule(body: dict):
    from adaptron.connectors.scheduler import IngestionScheduler, ScheduleConfig
    from adaptron.connectors.models import FetchQuery

    scheduler = IngestionScheduler()
    config = ScheduleConfig(
        connector_profile=body["profile"],
        query=FetchQuery(collection=body.get("collection", "")),
        cron=body.get("cron", "0 * * * *"),
    )
    schedule_id = await scheduler.add_schedule(config)
    return {"schedule_id": schedule_id}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    from adaptron.connectors.scheduler import IngestionScheduler

    scheduler = IngestionScheduler()
    await scheduler.remove_schedule(schedule_id)
    return {"status": "deleted"}
