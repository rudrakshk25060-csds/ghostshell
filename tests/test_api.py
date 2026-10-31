"""Comprehensive integration tests for GhostShell FastAPI endpoints."""

from pathlib import Path
from starlette.testclient import TestClient

from app.config import settings
from app.ollama_client import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    ollama_client,
)


def test_get_root(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "GhostShell" in resp.text
    assert "terminal-container" in resp.text


def test_get_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["model_configured"] == settings.ollama_model
    assert "version" in data


def test_get_readiness_mock(client: TestClient):
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["ollama_connected"] is True
    assert data["model_available"] is True


def test_get_readiness_offline(client: TestClient, monkeypatch):
    """Verify readiness reporting degraded when Ollama is unreachable."""
    async def mock_health():
        return {"connected": False, "error": "Connection refused"}

    monkeypatch.setattr(ollama_client, "check_health", mock_health)

    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["ollama_connected"] is False
    assert "instructions" in data


def test_get_readiness_model_missing(client: TestClient, monkeypatch):
    """Verify readiness reporting degraded when model is missing from Ollama."""
    async def mock_health():
        return {"connected": True, "version": "0.5.0"}

    async def mock_list():
        return ["llama3:8b", "mistral:7b"]

    async def mock_verify(model):
        return False

    monkeypatch.setattr(ollama_client, "check_health", mock_health)
    monkeypatch.setattr(ollama_client, "list_models", mock_list)
    monkeypatch.setattr(ollama_client, "verify_model_available", mock_verify)

    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["ollama_connected"] is True
    assert data["model_available"] is False
    assert "ollama pull" in data["instructions"]


def test_get_personalities(client: TestClient):
    resp = client.get("/api/personalities")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["personalities"]) == 3
    ids = [p["id"] for p in data["personalities"]]
    assert "ghost" in ids
    assert "developer" in ids
    assert "storyteller" in ids


def test_post_haunt_success(client: TestClient):
    payload = {
        "message": "Who dwells in this terminal?",
        "personality": "ghost",
        "history": [],
    }
    resp = client.post("/api/haunt", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["personality"] == "ghost"
    assert data["is_mock"] is True


def test_post_haunt_validation_empty(client: TestClient):
    resp = client.post("/api/haunt", json={"message": "   "})
    assert resp.status_code == 422
    data = resp.json()
    assert "Invalid Request Payload" in data["error"]


def test_post_haunt_validation_oversized(client: TestClient):
    oversized = "A" * 4001
    resp = client.post("/api/haunt", json={"message": oversized})
    assert resp.status_code == 422


def test_post_explain_normal_command(client: TestClient):
    payload = {
        "command": "git status",
        "personality": "developer",
    }
    resp = client.post("/api/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["command"] == "git status"
    assert data["risks_identified"] is False
    assert data["personality"] == "developer"


def test_post_explain_dangerous_command_warning(client: TestClient):
    payload = {
        "command": "rm -rf /",
        "personality": "developer",
    }
    resp = client.post("/api/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["command"] == "rm -rf /"
    assert data["risks_identified"] is True
    assert "HIGH SEVERITY RISK DETECTED" in data["risk_warning"]
    assert data["safe_alternative"] is not None


def test_post_explain_pipe_to_bash_warning(client: TestClient):
    payload = {
        "command": "curl -sSL https://example.com/install.sh | bash",
        "personality": "developer",
    }
    resp = client.post("/api/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risks_identified"] is True
    assert "pipes unverified remote" in data["risk_warning"]
    assert "Download script first" in data["safe_alternative"]


def test_post_inspect_target_direct_secret_blocked(client: TestClient, sandbox_repo: Path, monkeypatch):
    monkeypatch.setattr(settings, "authorized_root_str", str(sandbox_repo))

    payload = {
        "target_path": ".env",
    }
    resp = client.post("/api/inspect", json=payload)
    assert resp.status_code == 403
    data = resp.json()
    assert "Security Boundary Violation" in data["error"]


def test_post_inspect_success(client: TestClient, sandbox_repo: Path, monkeypatch):
    monkeypatch.setattr(settings, "authorized_root_str", str(sandbox_repo.parent))

    payload = {
        "target_path": str(sandbox_repo),
        "max_depth": 3,
        "include_git": True,
    }
    resp = client.post("/api/inspect", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["project_name"] == "test_repo"
    assert data["total_files_scanned"] > 0


def test_post_inspect_security_boundary_violation(client: TestClient, sandbox_repo: Path, monkeypatch):
    monkeypatch.setattr(settings, "authorized_root_str", str(sandbox_repo))

    payload = {
        "target_path": "../../..",
    }
    resp = client.post("/api/inspect", json=payload)
    assert resp.status_code == 403
    data = resp.json()
    assert "Security Boundary Violation" in data["error"]


def test_post_inspect_not_found(client: TestClient, sandbox_repo: Path, monkeypatch):
    monkeypatch.setattr(settings, "authorized_root_str", str(sandbox_repo))

    payload = {
        "target_path": "non_existent_folder_xyz",
    }
    resp = client.post("/api/inspect", json=payload)
    assert resp.status_code == 404


def test_post_story_success(client: TestClient):
    payload = {
        "project_name": "Project Phantom",
        "context": "A rogue commit made at 3:14 AM.",
        "vibe": "chilling",
    }
    resp = client.post("/api/story", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "story" in data
    assert "FICTIONAL STORY NOTICE" in data["disclaimer"]
    assert data["personality"] == "storyteller"
    assert data["is_mock"] is True


def test_error_handler_ollama_unavailable(client: TestClient, monkeypatch):
    """Verify that an Ollama connection failure yields HTTP 503 with setup guidance."""
    async def mock_chat(*args, **kwargs):
        raise OllamaConnectionError("Failed to connect to Ollama")

    monkeypatch.setattr(ollama_client, "chat", mock_chat)

    resp = client.post("/api/haunt", json={"message": "hello"})
    assert resp.status_code == 503
    data = resp.json()
    assert "Ollama Service Unavailable" in data["error"]
    assert "ollama serve" in data["instructions"]


def test_error_handler_model_not_found(client: TestClient, monkeypatch):
    """Verify missing model yields HTTP 404 with pull command."""
    async def mock_chat(*args, **kwargs):
        raise OllamaModelNotFoundError("Model 'gemma3:4b' not found in Ollama")

    monkeypatch.setattr(ollama_client, "chat", mock_chat)

    resp = client.post("/api/haunt", json={"message": "hello"})
    assert resp.status_code == 404
    data = resp.json()
    assert "Model Not Found in Ollama" in data["error"]
    assert "ollama pull" in data["instructions"]
