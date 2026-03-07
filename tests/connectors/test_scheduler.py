import pytest
from adaptron.connectors.scheduler import IngestionScheduler, ScheduleConfig
from adaptron.connectors.models import FetchQuery


@pytest.mark.asyncio
async def test_add_and_list_schedule(tmp_path):
    scheduler = IngestionScheduler(storage_path=tmp_path / "schedules.yaml")
    config = ScheduleConfig(
        connector_profile="mydb",
        query=FetchQuery(collection="users"),
        cron="0 * * * *",
    )
    schedule_id = await scheduler.add_schedule(config)
    assert schedule_id != ""
    schedules = await scheduler.list_schedules()
    assert len(schedules) == 1
    assert schedules[0].connector_profile == "mydb"


@pytest.mark.asyncio
async def test_remove_schedule(tmp_path):
    scheduler = IngestionScheduler(storage_path=tmp_path / "schedules.yaml")
    config = ScheduleConfig(
        connector_profile="mydb",
        query=FetchQuery(collection="users"),
        cron="0 * * * *",
    )
    schedule_id = await scheduler.add_schedule(config)
    await scheduler.remove_schedule(schedule_id)
    schedules = await scheduler.list_schedules()
    assert len(schedules) == 0


@pytest.mark.asyncio
async def test_incremental_checkpoint(tmp_path):
    scheduler = IngestionScheduler(storage_path=tmp_path / "schedules.yaml")
    config = ScheduleConfig(
        connector_profile="mydb",
        query=FetchQuery(collection="users"),
        cron="0 * * * *",
        mode="incremental",
        incremental_key="updated_at",
        last_checkpoint="2024-01-01",
    )
    schedule_id = await scheduler.add_schedule(config)
    schedules = await scheduler.list_schedules()
    assert schedules[0].mode == "incremental"
    assert schedules[0].last_checkpoint == "2024-01-01"
