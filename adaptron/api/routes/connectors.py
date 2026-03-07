"""API routes for connector management."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("/types")
def list_types():
    """List available connector types."""
    from adaptron.core.registry import global_registry
    types = global_registry.list_plugins("connector")
    return {"types": types}


@router.get("/profiles")
def list_profiles():
    """List saved connection profiles."""
    from adaptron.connectors.manager import ConnectionManager
    manager = ConnectionManager()
    profiles = manager.list_profiles()
    return {"profiles": profiles}


@router.post("/test")
async def test_connection(config: dict):
    """Test a connection configuration."""
    from adaptron.connectors.manager import ConnectionManager
    from adaptron.connectors.models import ConnectorConfig
    manager = ConnectionManager()
    try:
        connector_config = ConnectorConfig(**config)
        connector = await manager.connect_with_config(connector_config)
        await connector.disconnect()
        return {"status": "ok", "message": "Connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
