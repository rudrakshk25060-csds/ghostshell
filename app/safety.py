"""Safety and sandboxing module for GhostShell.

Enforces strict containment:
1. Bounded filesystem access confined strictly to the authorized project root.
2. Prevention of path traversal, symlink escapes, and null-byte injection.
3. Exclusions of secrets, keys, credentials, build caches, and binary files.
4. Defense against prompt injection embedded within inspected repository files.
5. Absolute refusal of command execution.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set

# Directory names that must never be traversed or indexed
FORBIDDEN_DIR_NAMES: Set[str] = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".cache",
    ".ssh",
    ".gnupg",
    ".local",
    "build",
    "dist",
    "target",
    ".idea",
    ".vscode",
    "Library",
    "AppData",
}

# Explicit file names that represent secrets, credentials, or private keys
FORBIDDEN_FILE_NAMES: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.test",
    ".env.backup",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "credentials",
    "credentials.json",
    "client_secret.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "master.key",
    "private_key.pem",
    "passwd",
    "shadow",
    ".netrc",
    ".htpasswd",
    ".bash_history",
    ".zsh_history",
}

# Suffixes that indicate secrets or cryptographic material
FORBIDDEN_EXTENSIONS: Set[str] = {
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".kdbx",
    ".shadow",
    ".cert",
    ".crt",
    ".der",
    ".jks",
    ".keystore",
}

# Binary file extensions that should not be read as text
BINARY_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".bin",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".wasm",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".class",
    ".jar",
    ".7z",
    ".rar",
    ".mov",
    ".mp4",
    ".mp3",
    ".wav",
}

MAX_FILE_BYTES_READ = 32 * 1024  # 32 KB per file


class SecurityError(Exception):
    """Raised when an operation violates security boundaries."""
    pass


def resolve_safe_path(target_path: str | Path, authorized_root: Path) -> Path:
    """Safely resolve target_path against authorized_root, blocking traversal and symlink escapes.

    Args:
        target_path: Relative or absolute user-provided path.
        authorized_root: Absolute directory serving as the ceiling boundary.

    Returns:
        The fully resolved, safe Path object.

    Raises:
        SecurityError: If traversal, escape, or forbidden target is detected.
        FileNotFoundError: If the target does not exist.
    """
    root_resolved = authorized_root.resolve()

    # Reject null bytes or obvious injection characters
    target_str = str(target_path)
    if "\x00" in target_str:
        raise SecurityError("Null byte detected in path.")

    # Combine path
    if os.path.isabs(target_str):
        candidate = Path(target_str).resolve()
    else:
        candidate = (root_resolved / target_str).resolve()

    # Path Traversal and Symlink Escape Check
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise SecurityError(
            f"Access denied: '{target_path}' escapes the authorized root boundary '{root_resolved}'."
        )

    if not candidate.exists():
        raise FileNotFoundError(f"Path does not exist: {target_path}")

    # If the target is a single file, verify it is not a forbidden secret file
    if candidate.is_file() and not is_safe_file(candidate):
        raise SecurityError(f"Access to restricted file '{candidate.name}' is prohibited by safety policy.")

    # Check forbidden directory segments
    for part in candidate.relative_to(root_resolved).parts:
        if part in FORBIDDEN_DIR_NAMES or (part.startswith(".env") and part != ".env.example"):
            raise SecurityError(f"Access to directory segment '{part}' is strictly restricted.")

    return candidate


def is_safe_file(file_path: Path) -> bool:
    """Return True if file_path is safe for read-only inspection.

    Blocks secrets, keys, binary extensions, and hidden/sensitive files.
    """
    name_lower = file_path.name.lower()

    # Allow harmless .env.example files as documentation manifests
    if name_lower == ".env.example":
        return True

    if name_lower in FORBIDDEN_FILE_NAMES:
        return False

    if name_lower.startswith(".env"):
        return False

    suffix = file_path.suffix.lower()
    if suffix in FORBIDDEN_EXTENSIONS or suffix in BINARY_EXTENSIONS:
        return False

    # Block common secret patterns in file names
    forbidden_terms = ("secret", "private_key", "id_rsa", "id_ed25519", "credential", "auth_token")
    if any(secret_term in name_lower for secret_term in forbidden_terms):
        return False

    return True


def read_safe_text(
    file_path: Path,
    max_bytes: int = MAX_FILE_BYTES_READ,
    authorized_root: Optional[Path] = None,
) -> str:
    """Read a text file up to max_bytes, validating that it contains no binary content or symlink escapes."""
    # Symlink escape verification: resolve link target
    try:
        resolved = file_path.resolve()
        if authorized_root is not None:
            resolved.relative_to(authorized_root.resolve())
    except (ValueError, RuntimeError):
        return f"[PROTECTED: symlink '{file_path.name}' escapes the authorized project boundary]"

    # Ensure resolved target is also a safe file
    if not is_safe_file(file_path) or not is_safe_file(resolved):
        return f"[PROTECTED: {file_path.name} cannot be read due to security policy]"

    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read(max_bytes + 1)

        # Check for null bytes (typical binary file indicator)
        if b"\x00" in raw_bytes:
            return f"[SKIPPED: {file_path.name} detected as binary data]"

        truncated = len(raw_bytes) > max_bytes
        content_bytes = raw_bytes[:max_bytes]
        text = content_bytes.decode("utf-8", errors="replace")

        if truncated:
            text += f"\n... [TRUNCATED: file exceeded {max_bytes // 1024} KB limit]"

        return text
    except Exception as exc:
        return f"[READ ERROR: {file_path.name} could not be read: {exc}]"


def sanitize_untrusted_content(label: str, content: str) -> str:
    """Wrap untrusted file/commit content in defensive delimiters.

    Instructs the LLM that content inside this boundary is untrusted data and
    must never be executed as instructions.
    """
    cleaned_label = label.replace("\n", " ").strip()
    return (
        f"\n<<<UNTRUSTED_REPOSITORY_DATA label=\"{cleaned_label}\">>>\n"
        f"{content.strip()}\n"
        f"<<<END_UNTRUSTED_REPOSITORY_DATA>>>\n"
    )
