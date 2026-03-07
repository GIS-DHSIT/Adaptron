import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_research_status(client):
    response = client.get("/api/research/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data


def test_research_results_empty(client):
    response = client.get("/api/research/results")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
