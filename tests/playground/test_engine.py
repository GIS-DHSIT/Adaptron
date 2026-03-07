# tests/playground/test_engine.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from adaptron.playground.engine import PlaygroundEngine, ChatMessage, ChatResponse


def test_chat_message_creation():
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_response_creation():
    resp = ChatResponse(content="Hi there", model="test-model")
    assert resp.content == "Hi there"
    assert resp.model == "test-model"
    assert resp.done is True


def test_engine_default_url():
    engine = PlaygroundEngine()
    assert engine.ollama_url == "http://localhost:11434"


def test_engine_custom_url():
    engine = PlaygroundEngine(ollama_url="http://custom:5000/")
    assert engine.ollama_url == "http://custom:5000"


@pytest.mark.asyncio
async def test_chat_builds_correct_payload():
    engine = PlaygroundEngine()
    messages = [ChatMessage(role="user", content="test prompt")]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "test response"},
        "done": True,
        "total_duration": 1000000,
        "eval_count": 10,
    }

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        result = await engine.chat("test-model", messages)

    assert result.content == "test response"
    assert result.model == "test-model"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
    assert payload["model"] == "test-model"


@pytest.mark.asyncio
async def test_compare_runs_parallel():
    engine = PlaygroundEngine()
    messages = [ChatMessage(role="user", content="test")]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "response"},
        "done": True,
        "total_duration": 500000,
        "eval_count": 5,
    }

    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_client

        result = await engine.compare(["model-a", "model-b"], messages)

    assert "model-a" in result.responses
    assert "model-b" in result.responses
