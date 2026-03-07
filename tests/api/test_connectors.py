"""Tests for API connector routes."""
import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_list_connector_types(client):
    # Import connectors to register them
    import adaptron.connectors.sqlite  # noqa: F401
    response = client.get("/api/connectors/types")
    assert response.status_code == 200
    data = response.json()
    assert "types" in data
    assert isinstance(data["types"], list)


def test_list_profiles_empty(client, tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTRON_CONNECTIONS_FILE", str(tmp_path / "connections.yaml"))
    response = client.get("/api/connectors/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["profiles"] == []


def test_test_connection_invalid(client):
    response = client.post("/api/connectors/test", json={"connector_type": "nonexistent"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
