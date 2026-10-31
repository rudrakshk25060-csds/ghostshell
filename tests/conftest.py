"""Pytest configuration and fixtures for GhostShell test suite."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Ensure mock mode is active by default during automated test runs."""
    monkeypatch.setattr(settings, "mock_mode", True)


@pytest.fixture
def client():
    """Synchronous test client for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sandbox_repo(tmp_path: Path):
    """Create a temporary sandbox repository containing safe files, secrets, and binary files."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Safe README
    (repo / "README.md").write_text("# Test Safe Project\nA demonstration repository for GhostShell.\nTODO: Fix daemon leak")

    # Safe python file
    (repo / "main.py").write_text("print('Ghost in the Machine')\n# FIXME: unhandled exception\n")

    # Safe package manifest
    (repo / "pyproject.toml").write_text("[project]\nname = 'test-safe-project'\nversion = '0.1.0'\n")

    # Secret files that MUST be filtered out
    (repo / ".env").write_text("DATABASE_URL=postgres://secret:password@localhost/db\nAPI_KEY=sk_test_12345\n")
    (repo / "id_rsa").write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n")
    (repo / "server.key").write_text("-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkq...\n-----END PRIVATE KEY-----\n")
    (repo / "credentials.json").write_text('{"token": "super_secret_oauth_token"}')

    # Binary file
    (repo / "compiled.pyc").write_bytes(b"\x00\x01\x02\x03\x04\x00\x00\x00")

    # File with embedded null byte
    (repo / "corrupted.txt").write_bytes(b"Text before null\x00text after null")

    # Subdirectory with another file
    sub = repo / "subfolder"
    sub.mkdir()
    (sub / "worker.py").write_text("def work(): pass\n")

    # Mock .git/logs/HEAD reflog
    git_logs = repo / ".git" / "logs"
    git_logs.mkdir(parents=True)
    reflog_content = (
        "0000000000000000000000000000000000000000 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b Author Name <author@example.com> 1700000000 +0000\tcommit (initial): Initial ritual commit\n"
        "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b 9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e Author Name <author@example.com> 1700001000 +0000\tcommit: Awaken the forgotten daemon\n"
    )
    (git_logs / "HEAD").write_text(reflog_content)

    return repo
