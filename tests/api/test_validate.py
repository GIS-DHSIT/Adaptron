import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_validate_status(client):
    response = client.get("/api/validate/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data

def test_validate_report_empty(client):
    response = client.get("/api/validate/report")
    assert response.status_code == 200
    data = response.json()
    assert "report" in data
