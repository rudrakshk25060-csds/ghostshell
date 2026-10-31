"""Read-only safe project inspection module for GhostShell.

Inspects bounded repository structure, safe configuration files, README, and
recent git commit logs without executing any shell commands or subprocesses.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.safety import (
    FORBIDDEN_DIR_NAMES,
    is_safe_file,
    read_safe_text,
    resolve_safe_path,
    sanitize_untrusted_content,
)

# Common key configuration and manifest files to prioritize
KEY_MANIFEST_FILES = [
    "README.md",
    "README.txt",
    "README",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Makefile",
    "CMakeLists.txt",
    ".gitignore",
]

# Signatures for technology detection
TECH_INDICATORS: Dict[str, str] = {
    "package.json": "JavaScript / Node.js",
    "tsconfig.json": "TypeScript",
    "requirements.txt": "Python",
    "pyproject.toml": "Python (Modern Packaging)",
    "Pipfile": "Python (Pipenv)",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java / Kotlin (Gradle)",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "docker-compose.yml": "Docker Compose",
    "Dockerfile": "Docker",
}


def parse_git_reflog_safely(repo_root: Path, max_commits: int = 5) -> List[Dict[str, str]]:
    """Safely extract recent commit messages from .git/logs/HEAD without using any subprocess.

    This guarantees zero command execution while providing authentic commit history.
    """
    commits: List[Dict[str, str]] = []
    git_log_file = repo_root / ".git" / "logs" / "HEAD"

    if not git_log_file.is_file():
        return commits

    try:
        # Read the last few kilobytes of the reflog
        with open(git_log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        # Parse from newest to oldest
        for line in reversed(lines[-max_commits * 2:]):
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                header, action_and_msg = parts
                header_tokens = header.split(" ")
                commit_hash = header_tokens[1][:7] if len(header_tokens) > 1 else "unknown"

                # Action and message format: 'commit: message' or 'commit (initial): message'
                msg = action_and_msg
                if ": " in action_and_msg:
                    action_type, msg_text = action_and_msg.split(": ", 1)
                    if "commit" in action_type:
                        msg = msg_text

                commits.append({
                    "hash": commit_hash,
                    "message": msg.strip(),
                })

            if len(commits) >= max_commits:
                break
    except Exception:
        # If parsing fails or git format differs, return empty list gracefully
        pass

    return commits


def inspect_directory(
    target_path_str: str = ".",
    max_depth: int = 3,
    include_git: bool = True,
    authorized_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Perform a strictly bounded, read-only inspection of a project directory.

    Args:
        target_path_str: Relative or absolute path within the authorized root.
        max_depth: Recursion limit for scanning directory hierarchy.
        include_git: Whether to attempt read-only extraction of git commits.
        authorized_root: Root directory ceiling (defaults to settings.authorized_root).

    Returns:
        Structured dictionary matching InspectResponse fields.
    """
    root = authorized_root or settings.authorized_root
    target_dir = resolve_safe_path(target_path_str, root)

    if not target_dir.is_dir():
        # If user pointed to a single file, treat parent as project
        target_dir = target_dir.parent

    project_name = target_dir.name
    tree_lines: List[str] = []
    important_files: List[str] = []
    detected_technologies: List[str] = []
    observations: List[str] = []
    readme_snippet: Optional[str] = None

    raw_context_segments: List[str] = []
    total_files_scanned = 0
    max_tree_entries = 45

    # 1. Walk directory up to max_depth
    for current_root, dirs, files in os.walk(target_dir):
        # In-place filter out forbidden directories
        dirs[:] = [
            d for d in dirs
            if d not in FORBIDDEN_DIR_NAMES and not d.startswith(".")
        ]

        curr_path = Path(current_root)
        rel_path = curr_path.relative_to(target_dir)
        depth = len(rel_path.parts)

        if depth >= max_depth:
            dirs.clear()  # Do not descend deeper

        indent = "  " * depth
        if rel_path.name:
            if len(tree_lines) < max_tree_entries:
                tree_lines.append(f"{indent}📁 {rel_path.name}/")

        for fname in sorted(files):
            total_files_scanned += 1
            fpath = curr_path / fname

            if not is_safe_file(fpath):
                continue

            # Technology detection
            if fname in TECH_INDICATORS:
                tech = TECH_INDICATORS[fname]
                if tech not in detected_technologies:
                    detected_technologies.append(tech)

            if len(tree_lines) < max_tree_entries:
                tree_lines.append(f"{indent}  📄 {fname}")

            # Collect important manifest or configuration files
            rel_file_str = str((rel_path / fname).as_posix())
            if fname in KEY_MANIFEST_FILES:
                important_files.append(rel_file_str)

    if len(tree_lines) >= max_tree_entries:
        tree_lines.append("  ... [directory tree truncated for brevity]")

    # 2. Extract README if present
    readme_candidates = ["README.md", "README.txt", "README", "readme.md"]
    for rname in readme_candidates:
        rpath = target_dir / rname
        if rpath.is_file() and is_safe_file(rpath):
            raw_readme = read_safe_text(rpath, max_bytes=8192, authorized_root=root)
            readme_snippet = raw_readme[:1200]
            raw_context_segments.append(
                sanitize_untrusted_content(f"README: {rname}", raw_readme[:3000])
            )
            break

    # 3. Read snippets of up to 3 key manifest files
    manifests_read = 0
    for imp_rel in important_files:
        if imp_rel.endswith(("README.md", "README")):
            continue
        imp_path = target_dir / imp_rel
        if imp_path.is_file() and manifests_read < 3:
            manifest_text = read_safe_text(imp_path, max_bytes=2048, authorized_root=root)
            raw_context_segments.append(
                sanitize_untrusted_content(f"MANIFEST: {imp_rel}", manifest_text[:1500])
            )
            manifests_read += 1

    # 4. Git history extraction (safe read-only reflog)
    recent_commits: List[Dict[str, str]] = []
    if include_git:
        recent_commits = parse_git_reflog_safely(target_dir, max_commits=5)
        if recent_commits:
            commit_text = "\n".join([f"- {c['hash']}: {c['message']}" for c in recent_commits])
            raw_context_segments.append(
                sanitize_untrusted_content("RECENT_GIT_COMMITS", commit_text)
            )

    # 5. Formulate human-readable observations
    if detected_technologies:
        observations.append(f"Primary technology stack: {', '.join(detected_technologies)}.")
    else:
        observations.append("No standard package manifest found (likely custom script or documentation repository).")

    if readme_snippet:
        observations.append("Project includes documentation describing its purpose.")
    else:
        observations.append("No top-level README detected; the repository's intent must be inferred from structure.")

    if recent_commits:
        observations.append(f"Discovered {len(recent_commits)} recent Git commits in the reflog history.")
    else:
        observations.append("No active Git commit history accessible or repository has clean/empty reflog.")

    # Check for unfinished clues or ghost themes
    todo_count = 0
    for segment in raw_context_segments:
        todo_count += segment.count("TODO") + segment.count("FIXME")
    if todo_count > 0:
        observations.append(f"Found {todo_count} TODO/FIXME markers lingering in the scanned files.")

    # 6. Build combined sanitized summary bounded by max_context_chars
    combined_raw_context = "\n".join(raw_context_segments)
    max_chars = settings.max_context_chars
    if len(combined_raw_context) > max_chars:
        combined_raw_context = combined_raw_context[:max_chars] + "\n[CONTEXT CLAMPED DUE TO SIZE LIMIT]"

    return {
        "resolved_path": str(target_dir),
        "project_name": project_name,
        "readme_snippet": readme_snippet,
        "key_technologies": detected_technologies,
        "important_files": important_files,
        "directory_tree": tree_lines,
        "recent_commits": recent_commits,
        "total_files_scanned": total_files_scanned,
        "context_char_count": len(combined_raw_context),
        "observations": observations,
        "sanitized_context_summary": combined_raw_context,
        "status": "success",
    }
