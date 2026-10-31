"""Main FastAPI application for GhostShell — The Ghost in Your Terminal.

Provides the REST API and serves the retro haunted terminal frontend.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.inspector import inspect_directory
from app.ollama_client import (
    OllamaAPIError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    ollama_client,
)
from app.prompts import (
    build_chat_system_prompt,
    build_command_explain_prompt,
    build_story_prompt,
)
from app.safety import SecurityError
from app.schemas import (
    ExplainRequest,
    ExplainResponse,
    HauntRequest,
    HauntResponse,
    HealthResponse,
    InspectRequest,
    InspectResponse,
    Personality,
    ReadyResponse,
    StoryRequest,
    StoryResponse,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [GhostShell]: %(message)s",
)
logger = logging.getLogger("ghostshell")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    logger.info("Initializing GhostShell terminal companion...")
    logger.info(f"Target Ollama URL: {settings.ollama_base_url}")
    logger.info(f"Target Model: {settings.ollama_model}")
    logger.info(f"Authorized Project Root: {settings.authorized_root}")
    if settings.mock_mode:
        logger.warning("ATTENTION: GHOSTSHELL_MOCK_MODE is ENABLED. Ollama responses are simulated.")
    yield
    logger.info("GhostShell powering down. The ghost sleeps.")


app = FastAPI(
    title="GhostShell",
    description="A local-first, haunted AI developer companion powered by Gemma 3 4B via Ollama.",
    version=__version__,
    lifespan=lifespan,
)

# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------------
# Custom Exception Handlers
# --------------------------------------------------------------------------

@app.exception_handler(OllamaConnectionError)
async def handle_ollama_conn_error(request: Request, exc: OllamaConnectionError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "Ollama Service Unavailable",
            "detail": str(exc),
            "instructions": (
                "1. Ensure Ollama is installed on your machine (https://ollama.com).\n"
                "2. Start Ollama with `ollama serve` or open the Ollama application.\n"
                f"3. Verify it is listening on {settings.ollama_base_url}."
            ),
        },
    )


@app.exception_handler(OllamaModelNotFoundError)
async def handle_ollama_model_missing(request: Request, exc: OllamaModelNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Model Not Found in Ollama",
            "detail": str(exc),
            "instructions": f"Pull the model locally by running:\n  ollama pull {settings.ollama_model}",
        },
    )


@app.exception_handler(OllamaTimeoutError)
async def handle_ollama_timeout(request: Request, exc: OllamaTimeoutError):
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={
            "error": "Inference Timeout",
            "detail": str(exc),
            "instructions": "The local model took too long to generate. Try a shorter prompt or increase GHOSTSHELL_READ_TIMEOUT.",
        },
    )


@app.exception_handler(SecurityError)
async def handle_security_violation(request: Request, exc: SecurityError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "Security Boundary Violation",
            "detail": str(exc),
            "authorized_root": str(settings.authorized_root),
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    errors = [f"{e.get('loc', ['field'])[-1]}: {e.get('msg')}" for e in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid Request Payload",
            "details": errors,
        },
    )


# --------------------------------------------------------------------------
# Core Endpoints
# --------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the retro haunted terminal frontend."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(index_file)


@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"])
async def get_health():
    """Application health endpoint. Returns status without claiming the model is ready."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        model_configured=settings.ollama_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/ready", response_model=ReadyResponse, tags=["Diagnostics"])
async def get_readiness():
    """Readiness endpoint. Evaluates live Ollama connectivity and configured model presence."""
    health_info = await ollama_client.check_health()
    connected = health_info.get("connected", False)

    if not connected:
        return ReadyResponse(
            status="degraded",
            ollama_connected=False,
            model_available=False,
            model_name=settings.ollama_model,
            base_url=settings.ollama_base_url,
            available_models=[],
            message="Ollama is unreachable. Start local Ollama service to enable AI features.",
            instructions=f"Run `ollama serve` and ensure {settings.ollama_base_url} is active.",
        )

    available_models = await ollama_client.list_models()
    model_ok = await ollama_client.verify_model_available(settings.ollama_model)

    if not model_ok:
        return ReadyResponse(
            status="degraded",
            ollama_connected=True,
            model_available=False,
            model_name=settings.ollama_model,
            base_url=settings.ollama_base_url,
            available_models=available_models,
            message=f"Ollama is running, but configured model '{settings.ollama_model}' is not pulled.",
            instructions=f"Run `ollama pull {settings.ollama_model}` in your terminal.",
        )

    return ReadyResponse(
        status="ready",
        ollama_connected=True,
        model_available=True,
        model_name=settings.ollama_model,
        base_url=settings.ollama_base_url,
        available_models=available_models,
        message=f"All systems operational. Local {settings.ollama_model} model is ready for inference.",
        instructions=None,
    )


@app.get("/api/personalities", tags=["Features"])
async def list_personalities():
    """Return available terminal personalities."""
    return {
        "personalities": [
            {
                "id": Personality.GHOST.value,
                "name": "Ghost in the Machine",
                "tagline": "Mysterious, atmospheric, poetic, yet technically rigorous.",
            },
            {
                "id": Personality.DEVELOPER.value,
                "name": "Systems Architect",
                "tagline": "Direct, technical, zero-fluff pragmatism.",
            },
            {
                "id": Personality.STORYTELLER.value,
                "name": "Terminal Cryptid",
                "tagline": "Spins eerie, fictional horror microfiction from code remnants.",
            },
        ]
    }


@app.post("/api/haunt", response_model=HauntResponse, tags=["Features"])
async def haunt_chat(request: HauntRequest):
    """Interact with the local Gemma model under the selected personality."""
    system_prompt = build_chat_system_prompt(request.personality)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    # Append bounded conversation history
    for item in request.history:
        messages.append({"role": item.role, "content": item.content})

    # Append current user prompt
    messages.append({"role": "user", "content": request.message})

    result = await ollama_client.chat(messages)

    return HauntResponse(
        reply=result["reply"],
        personality=request.personality,
        model=result["model"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        is_mock=result.get("is_mock", False),
    )


@app.post("/api/explain", response_model=ExplainResponse, tags=["Features"])
async def explain_command(request: ExplainRequest):
    """Explain a shell command without executing it.

    Analyzes command intent, flag parameters, potential destruction risks,
    and safer alternatives. Never executes commands via subprocess or shell.
    """
    raw_cmd = request.command.strip()

    # Pre-screen known high-risk command patterns for instant risk warning flags
    dangerous_patterns = [
        ("rm -rf /", "Attempts to delete the entire filesystem recursively from root."),
        ("rm -rf *", "Permanently deletes all files in current directory without prompt."),
        ("rm -rf", "Recursive, forced file deletion without confirmation prompt."),
        (":(){ :|:& };:", "Fork bomb: recursively spawns processes until system resources are exhausted."),
        ("mkfs", "Formats a drive partition, destroying all contained data."),
        ("dd if=", "Low-level block writer capable of wiping partition tables or drives."),
        ("> /dev/sda", "Direct write to primary storage block device, causing total corruption."),
        ("> /dev/", "Direct write to a raw system device node, risking severe hardware/filesystem damage."),
        ("chmod -R 777", "Removes all permission boundaries recursively, creating massive security vulnerability."),
        ("chmod 777", "Grants read, write, and execute permissions to all users on the system."),
        ("| bash", "Directly pipes unverified remote or command output into an executing shell."),
        ("| sh", "Directly pipes unverified remote or command output into an executing shell."),
    ]

    risks_identified = False
    risk_warning: str | None = None
    safe_alternative: str | None = None

    for pattern, warning_desc in dangerous_patterns:
        if pattern in raw_cmd:
            risks_identified = True
            risk_warning = f"HIGH SEVERITY RISK DETECTED: {warning_desc}"
            if "rm -rf" in raw_cmd:
                safe_alternative = "Use `trash` CLI, or inspect with `ls -la` / `find` before targeted deletion."
            elif "chmod" in raw_cmd:
                safe_alternative = "Apply least privilege: `chmod 755` for directories and `chmod 644` for files."
            elif "| bash" in raw_cmd or "| sh" in raw_cmd:
                safe_alternative = "Download script first, inspect its contents with a text editor, and run manually."
            break

    # Build prompt for Gemma
    messages = build_command_explain_prompt(raw_cmd, request.personality)
    result = await ollama_client.chat(messages)

    return ExplainResponse(
        command=raw_cmd,
        explanation=result["reply"],
        risks_identified=risks_identified,
        risk_warning=risk_warning,
        safe_alternative=safe_alternative,
        personality=request.personality,
        model=result["model"],
        is_mock=result.get("is_mock", False),
    )


@app.post("/api/inspect", response_model=InspectResponse, tags=["Features"])
async def inspect_project(request: InspectRequest):
    """Safely inspect a project directory within the authorized boundary.

    Collects README, file tree, manifests, and git history without running commands.
    """
    try:
        data = inspect_directory(
            target_path_str=request.target_path,
            max_depth=request.max_depth,
            include_git=request.include_git,
            authorized_root=settings.authorized_root,
        )
        return InspectResponse(
            resolved_path=data["resolved_path"],
            project_name=data["project_name"],
            readme_snippet=data["readme_snippet"],
            key_technologies=data["key_technologies"],
            important_files=data["important_files"],
            directory_tree=data["directory_tree"],
            recent_commits=data["recent_commits"],
            total_files_scanned=data["total_files_scanned"],
            context_char_count=data["context_char_count"],
            observations=data["observations"],
            sanitized_context_summary=data["sanitized_context_summary"],
            status=data["status"],
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/story", response_model=StoryResponse, tags=["Features"])
async def generate_ghost_story(request: StoryRequest):
    """Generate a fictional horror micro-story inspired by repository metadata."""
    disclaimer = (
        "FICTIONAL STORY NOTICE: The following tale is an artistic work of fiction "
        "inspired by repository metadata. It does not reflect real events, software bugs, "
        "or actual individuals."
    )

    project_name = request.project_name or "The Forgotten Repository"
    context = request.context or "A desolate repository whose last commit was made at 3:00 AM."
    vibe = request.vibe or "eerie and atmospheric"

    messages = build_story_prompt(project_name, context, vibe)
    result = await ollama_client.chat(messages)

    return StoryResponse(
        story=result["reply"],
        disclaimer=disclaimer,
        inspired_by=project_name,
        personality=Personality.STORYTELLER,
        model=result["model"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        is_mock=result.get("is_mock", False),
    )
