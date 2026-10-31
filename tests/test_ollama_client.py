"""Tests for Ollama client communication, payload construction, and error mapping."""

import pytest
import httpx

from app.ollama_client import (
    OllamaAPIError,
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)


@pytest.mark.asyncio
async def test_ollama_mock_mode():
    client = OllamaClient(mock_mode=True, model="gemma3:4b")
    health = await client.check_health()
    assert health["connected"] is True

    models = await client.list_models()
    assert "gemma3:4b" in models

    available = await client.verify_model_available("gemma3:4b")
    assert available is True

    result = await client.chat([{"role": "user", "content": "Hello phantom"}])
    assert result["is_mock"] is True
    assert "[TEST-MOCK: gemma3:4b]" in result["reply"]


@pytest.mark.asyncio
async def test_ollama_connection_error(monkeypatch):
    """Verify that a network connection error is cleanly caught and transformed."""
    async def mock_post(*args, **kwargs):
        raise httpx.ConnectError("Failed to connect")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = OllamaClient(mock_mode=False)
    with pytest.raises(OllamaConnectionError) as exc_info:
        await client.chat([{"role": "user", "content": "ping"}])
    assert "Cannot connect to local Ollama" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_model_not_found(monkeypatch):
    """Verify 404 response raises OllamaModelNotFoundError."""
    mock_resp = httpx.Response(status_code=404, text="model 'gemma3:4b' not found")

    async def mock_post(*args, **kwargs):
        return mock_resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = OllamaClient(mock_mode=False, model="gemma3:4b")
    with pytest.raises(OllamaModelNotFoundError) as exc_info:
        await client.chat([{"role": "user", "content": "ping"}])
    assert "ollama pull gemma3:4b" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_timeout(monkeypatch):
    """Verify httpx TimeoutException raises OllamaTimeoutError."""
    async def mock_post(*args, **kwargs):
        raise httpx.ReadTimeout("Request timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = OllamaClient(mock_mode=False)
    with pytest.raises(OllamaTimeoutError) as exc_info:
        await client.chat([{"role": "user", "content": "ping"}])
    assert "inference timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_payload_structure(monkeypatch):
    """Verify correct payload parameters sent to Ollama /api/chat."""
    captured_payload = {}

    async def mock_post(self, url, json=None, **kwargs):
        nonlocal captured_payload
        captured_payload = json
        return httpx.Response(
            status_code=200,
            json={
                "model": "gemma3:4b",
                "message": {"role": "assistant", "content": "The circuits hum."},
                "total_duration": 45000,
            },
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    client = OllamaClient(mock_mode=False, model="gemma3:4b")
    messages = [
        {"role": "system", "content": "You are Ghost."},
        {"role": "user", "content": "Status?"},
    ]
    resp = await client.chat(messages, temperature=0.5)

    assert resp["reply"] == "The circuits hum."
    assert captured_payload["model"] == "gemma3:4b"
    assert captured_payload["messages"] == messages
    assert captured_payload["stream"] is False
    assert captured_payload["options"]["temperature"] == 0.5
