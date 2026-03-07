"""Ingestion scheduler with YAML-based schedule storage."""
from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from adaptron.connectors.models import FetchQuery


@dataclass
class ScheduleConfig:
    connector_profile: str
    query: FetchQuery
    cron: str  # e.g. "0 * * * *"
    mode: str = "full"  # "full" or "incremental"
    incremental_key: str | None = None  # column to track for incremental
    last_checkpoint: Any = None
    output_format: str | None = None
    enabled: bool = True
    schedule_id: str = ""  # auto-generated UUID


class IngestionScheduler:
    """Stores and manages ingestion schedules in a YAML file."""

    def __init__(self, storage_path: Path | None = None) -> None:
        if storage_path is None:
            env_path = os.environ.get("ADAPTRON_SCHEDULES_FILE")
            if env_path:
                storage_path = Path(env_path)
            else:
                storage_path = Path.home() / ".adaptron" / "schedules.yaml"
        self._storage_path = storage_path
        self._schedules: dict[str, ScheduleConfig] = {}
        self._load()

    def _load(self) -> None:
        """Read schedules from YAML file."""
        if not self._storage_path.exists():
            self._schedules = {}
            return
        data = yaml.safe_load(self._storage_path.read_text(encoding="utf-8")) or {}
        schedules_data = data.get("schedules", {})
        self._schedules = {}
        for sid, sdata in schedules_data.items():
            query_data = sdata.pop("query", {})
            query = FetchQuery(**query_data)
            self._schedules[sid] = ScheduleConfig(
                query=query,
                schedule_id=sid,
                **sdata,
            )

    def _save(self) -> None:
        """Write schedules to YAML file."""
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        schedules_data: dict[str, Any] = {}
        for sid, config in self._schedules.items():
            data = asdict(config)
            data.pop("schedule_id", None)
            # Clean None values
            data = {k: v for k, v in data.items() if v is not None}
            # Clean empty options in query
            if "query" in data and "options" in data["query"] and not data["query"]["options"]:
                del data["query"]["options"]
            schedules_data[sid] = data
        self._storage_path.write_text(
            yaml.dump({"schedules": schedules_data}, default_flow_style=False),
            encoding="utf-8",
        )

    async def add_schedule(self, config: ScheduleConfig) -> str:
        """Add a new schedule, generating a UUID. Returns the schedule_id."""
        schedule_id = str(uuid.uuid4())
        config.schedule_id = schedule_id
        self._schedules[schedule_id] = config
        self._save()
        return schedule_id

    async def remove_schedule(self, schedule_id: str) -> None:
        """Remove a schedule by ID."""
        self._schedules.pop(schedule_id, None)
        self._save()

    async def list_schedules(self) -> list[ScheduleConfig]:
        """Return all schedules."""
        return list(self._schedules.values())

    async def run_now(self, schedule_id: str) -> None:
        """Execute the schedule immediately (connect, fetch, etc.)."""
        if schedule_id not in self._schedules:
            raise KeyError(f"Schedule '{schedule_id}' not found")
        config = self._schedules[schedule_id]
        from adaptron.connectors.manager import ConnectionManager

        manager = ConnectionManager()
        connector = await manager.connect(config.connector_profile)
        try:
            await connector.fetch(config.query)
        finally:
            await connector.disconnect()
