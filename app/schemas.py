"""Pydantic schemas for GhostShell API requests and responses."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Personality(str, Enum):
    """The three mystical personalities of GhostShell."""
    GHOST = "ghost"
    DEVELOPER = "developer"
    STORYTELLER = "storyteller"


class ChatMessage(BaseModel):
    """A single message turn in conversation history."""
    role: str = Field(description="Role: user or assistant")
    content: str = Field(min_length=1, max_length=4000, description="Message text")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("user", "assistant", "system"):
            raise ValueError("Role must be 'user', 'assistant', or 'system'")
        return clean


class HauntRequest(BaseModel):
    """Request payload for /api/haunt."""
    message: str = Field(
        min_length=1,
        max_length=4000,
        description="The query or terminal phrase spoken to GhostShell."
    )
    personality: Personality = Field(
        default=Personality.GHOST,
        description="Selected AI persona: ghost, developer, or storyteller."
    )
    history: List[ChatMessage] = Field(
        default_factory=list,
        max_length=10,
        description="Bounded conversation history (max 10 turns)."
    )

    @field_validator("message")
    @classmethod
    def non_empty_message(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or whitespace only.")
        return trimmed


class HauntResponse(BaseModel):
    """Response payload for /api/haunt."""
    reply: str
    personality: Personality
    model: str
    timestamp: str
    is_mock: bool = False


class ExplainRequest(BaseModel):
    """Request payload for /api/explain."""
    command: str = Field(
        min_length=1,
        max_length=1000,
        description="The shell command string to analyze and explain without execution."
    )
    personality: Personality = Field(
        default=Personality.DEVELOPER,
        description="Personality used to frame the explanation."
    )

    @field_validator("command")
    @classmethod
    def non_empty_command(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Command cannot be empty or whitespace only.")
        return trimmed


class ExplainResponse(BaseModel):
    """Response payload for /api/explain."""
    command: str
    explanation: str
    risks_identified: bool
    risk_warning: Optional[str] = None
    safe_alternative: Optional[str] = None
    personality: Personality
    model: str
    is_mock: bool = False


class InspectRequest(BaseModel):
    """Request payload for /api/inspect."""
    target_path: str = Field(
        default=".",
        max_length=500,
        description="Relative or absolute path within the authorized project root."
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Directory recursion depth."
    )
    include_git: bool = Field(
        default=True,
        description="Whether to safely extract read-only Git commit metadata."
    )


class InspectResponse(BaseModel):
    """Response payload for /api/inspect."""
    resolved_path: str
    project_name: str
    readme_snippet: Optional[str] = None
    key_technologies: List[str]
    important_files: List[str]
    directory_tree: List[str]
    recent_commits: List[Dict[str, str]]
    total_files_scanned: int
    context_char_count: int
    observations: List[str]
    sanitized_context_summary: str
    status: str


class StoryRequest(BaseModel):
    """Request payload for /api/story."""
    project_name: Optional[str] = Field(
        default="The Forgotten Repository",
        max_length=200,
        description="Name of the project inspiring the story."
    )
    context: Optional[str] = Field(
        default="",
        max_length=8000,
        description="Sanitized metadata or commit notes to inspire the fiction."
    )
    vibe: Optional[str] = Field(
        default="eerie",
        max_length=100,
        description="Atmospheric mood for the ghost story."
    )


class StoryResponse(BaseModel):
    """Response payload for /api/story."""
    story: str
    disclaimer: str
    inspired_by: str
    personality: Personality = Personality.STORYTELLER
    model: str
    timestamp: str
    is_mock: bool = False


class HealthResponse(BaseModel):
    """Response payload for /health."""
    status: str
    version: str
    model_configured: str
    timestamp: str


class ReadyResponse(BaseModel):
    """Response payload for /ready."""
    status: str
    ollama_connected: bool
    model_available: bool
    model_name: str
    base_url: str
    available_models: List[str]
    message: str
    instructions: Optional[str] = None
