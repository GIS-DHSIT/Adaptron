import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTRON_SCHEDULES_FILE", str(tmp_path / "schedules.yaml"))
    app = create_app()
    return TestClient(app)


def test_list_schedules_empty(client):
    response = client.get("/api/schedules")
    assert response.status_code == 200
    assert response.json()["schedules"] == []


def test_create_and_delete_schedule(client):
    response = client.post("/api/schedules", json={"profile": "mydb", "collection": "users", "cron": "0 * * * *"})
    assert response.status_code == 200
    schedule_id = response.json()["schedule_id"]

    response = client.delete(f"/api/schedules/{schedule_id}")
    assert response.status_code == 200

    response = client.get("/api/schedules")
    assert response.json()["schedules"] == []
