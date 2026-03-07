# tests/api/test_playground.py
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from adaptron.api.main import create_app


def _get_client():
    return TestClient(create_app())


def test_playground_models_endpoint_ollama_down():
    """When Ollama is not running, return 503."""
    client = _get_client()

    with patch("adaptron.playground.engine.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        resp = client.get("/api/playground/models")
    assert resp.status_code == 503


def test_playground_chat_non_streaming():
    """Test non-streaming chat endpoint with mocked Ollama."""
    client = _get_client()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Hello from the model"},
        "done": True,
        "total_duration": 1000,
        "eval_count": 5,
    }

    with patch("adaptron.playground.engine.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        resp = client.post("/api/playground/chat", json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Hello from the model"
