"""Tests for read-only project inspection."""

from pathlib import Path
from app.inspector import inspect_directory, parse_git_reflog_safely


def test_inspect_directory_basic(sandbox_repo: Path):
    result = inspect_directory(
        target_path_str=str(sandbox_repo),
        max_depth=3,
        include_git=True,
        authorized_root=sandbox_repo.parent,
    )

    assert result["status"] == "success"
    assert result["project_name"] == "test_repo"
    assert "README.md" in result["important_files"]
    assert "Python (Modern Packaging)" in result["key_technologies"]

    # Ensure secret files are NOT in important files or raw context
    for f in result["important_files"]:
        assert not f.endswith(".env")
        assert not f.endswith(".key")
        assert not f.endswith("id_rsa")

    assert "DATABASE_URL" not in result["sanitized_context_summary"]
    assert "BEGIN RSA PRIVATE KEY" not in result["sanitized_context_summary"]


def test_parse_git_reflog_safely(sandbox_repo: Path):
    commits = parse_git_reflog_safely(sandbox_repo, max_commits=5)
    assert len(commits) == 2
    # Verify commit messages parsed accurately without subprocess
    messages = [c["message"] for c in commits]
    assert "Awaken the forgotten daemon" in messages
    assert "Initial ritual commit" in messages


def test_todo_observation_discovery(sandbox_repo: Path):
    result = inspect_directory(
        target_path_str=str(sandbox_repo),
        authorized_root=sandbox_repo.parent,
    )
    obs_text = " ".join(result["observations"])
    assert "TODO/FIXME" in obs_text or "lingering" in obs_text


def test_context_clamping_enforced(sandbox_repo: Path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_context_chars", 50)

    result = inspect_directory(
        target_path_str=str(sandbox_repo),
        authorized_root=sandbox_repo.parent,
    )
    assert "[CONTEXT CLAMPED DUE TO SIZE LIMIT]" in result["sanitized_context_summary"]
