"""Configuration module for GhostShell.

Reads settings from environment variables and an optional .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file if available
load_dotenv()


class Settings(BaseModel):
    """GhostShell application configuration settings."""

    # Ollama service configuration
    ollama_base_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    )
    ollama_model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()
    )

    # Context and safety thresholds
    max_context_chars: int = Field(
        default_factory=lambda: int(os.getenv("GHOSTSHELL_MAX_CONTEXT_CHARS", "12000"))
    )
    connect_timeout: float = Field(
        default_factory=lambda: float(os.getenv("GHOSTSHELL_CONNECT_TIMEOUT", "5.0"))
    )
    read_timeout: float = Field(
        default_factory=lambda: float(os.getenv("GHOSTSHELL_READ_TIMEOUT", "90.0"))
    )

    # Safe inspection boundaries
    authorized_root_str: Optional[str] = Field(
        default_factory=lambda: os.getenv("GHOSTSHELL_AUTHORIZED_ROOT")
    )

    # Server binding
    host: str = Field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    # Testing / Mock mode (strictly separated from real production Ollama)
    mock_mode: bool = Field(
        default_factory=lambda: os.getenv("GHOSTSHELL_MOCK_MODE", "false").lower() in ("1", "true", "yes")
    )

    @property
    def authorized_root(self) -> Path:
        """Resolve the effective authorized directory for project inspection.

        If GHOSTSHELL_AUTHORIZED_ROOT is specified, resolve it strictly.
        Otherwise, default safely to the parent directory of this ghostshell repo.
        """
        if self.authorized_root_str and self.authorized_root_str.strip():
            candidate = Path(self.authorized_root_str.strip()).expanduser().resolve()
            return candidate

        # Default: directory containing this repo or current working directory
        current_dir = Path.cwd().resolve()
        return current_dir


# Global singleton instance
settings = Settings()
