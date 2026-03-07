# tests/api/test_api.py
import pytest
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_wizard_recommend(client):
    resp = client.post("/api/wizard/recommend", json={
        "primary_goal": "qa_docs", "data_sources": ["docs"],
        "data_freshness": "static", "hardware": "mid",
        "timeline": "medium", "accuracy": "professional", "model_size": "small",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "training_modes" in data
    assert "base_model" in data
