"""Asynchronous Ollama API client for GhostShell.

Interacts with the local Ollama service to run Google's Gemma 3 4B model.
Includes robust error categorization, health checks, and a safe mock mode for tests.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama interactions."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when Ollama is unreachable (connection refused, service not running)."""
    pass


class OllamaModelNotFoundError(OllamaError):
    """Raised when the specified model (e.g. gemma3:4b) is not installed in Ollama."""
    pass


class OllamaTimeoutError(OllamaError):
    """Raised when communication with Ollama times out."""
    pass


class OllamaAPIError(OllamaError):
    """Raised when Ollama responds with an unexpected error."""
    pass


class OllamaClient:
    """Async client for local Ollama inference."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
        mock_mode: Optional[bool] = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.connect_timeout = connect_timeout or settings.connect_timeout
        self.read_timeout = read_timeout or settings.read_timeout
        self._mock_mode = mock_mode

    @property
    def mock_mode(self) -> bool:
        if self._mock_mode is not None:
            return self._mock_mode
        return settings.mock_mode

    def _get_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=10.0,
            pool=5.0,
        )
        return httpx.AsyncClient(timeout=timeout)

    async def check_health(self) -> Dict[str, Any]:
        """Check if the local Ollama daemon is reachable and retrieve its version."""
        if self.mock_mode:
            return {
                "connected": True,
                "version": "0.5.0-mock",
                "base_url": self.base_url,
            }

        url = f"{self.base_url}/api/version"
        try:
            async with self._get_client() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "connected": True,
                        "version": data.get("version", "unknown"),
                        "base_url": self.base_url,
                    }
                else:
                    return {
                        "connected": False,
                        "error": f"Ollama returned HTTP {resp.status_code}",
                        "base_url": self.base_url,
                    }
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            return {
                "connected": False,
                "error": f"Connection refused at {self.base_url}. Ensure Ollama is running (`ollama serve`).",
                "base_url": self.base_url,
            }
        except httpx.TimeoutException:
            return {
                "connected": False,
                "error": f"Connection to {self.base_url} timed out.",
                "base_url": self.base_url,
            }
        except Exception as exc:
            return {
                "connected": False,
                "error": str(exc),
                "base_url": self.base_url,
            }

    async def list_models(self) -> List[str]:
        """Fetch the list of installed model names and tags in Ollama."""
        if self.mock_mode:
            return [self.model, "gemma3:4b", "gemma2:2b"]

        url = f"{self.base_url}/api/tags"
        try:
            async with self._get_client() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return models
                return []
        except Exception as exc:
            logger.warning(f"Failed to fetch model list from Ollama: {exc}")
            return []

    async def verify_model_available(self, target_model: Optional[str] = None) -> bool:
        """Verify if target_model (or self.model) is installed locally in Ollama."""
        desired = target_model or self.model
        available = await self.list_models()

        # Check exact match or base tag match (e.g., 'gemma3:4b' matches 'gemma3:4b' or 'gemma3:4b-instruct')
        for m in available:
            if m == desired or m.startswith(f"{desired}:") or desired.startswith(f"{m}:"):
                return True
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Send chat messages to the local Ollama /api/chat endpoint.

        Args:
            messages: List of message objects with 'role' and 'content'.
            model: Optional model override.
            temperature: Sampling temperature.

        Returns:
            Dict containing the assistant reply, model used, and token stats.

        Raises:
            OllamaConnectionError: If daemon is unreachable.
            OllamaModelNotFoundError: If requested model is missing.
            OllamaTimeoutError: If inference times out.
            OllamaAPIError: For other API failures.
        """
        active_model = model or self.model

        if self.mock_mode:
            # Deterministic response for automated test suites
            last_user_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user_msg = m.get("content", "")
                    break

            return {
                "reply": f"[TEST-MOCK: {active_model}] The phantom speaks: Echoing '{last_user_msg[:60]}'.",
                "model": active_model,
                "total_duration": 120000,
                "is_mock": True,
            }

        url = f"{self.base_url}/api/chat"
        payload = {
            "model": active_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            async with self._get_client() as client:
                resp = await client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    message = data.get("message", {})
                    reply_text = message.get("content", "")
                    return {
                        "reply": reply_text.strip(),
                        "model": data.get("model", active_model),
                        "total_duration": data.get("total_duration", 0),
                        "is_mock": False,
                    }

                if resp.status_code == 404:
                    raise OllamaModelNotFoundError(
                        f"Model '{active_model}' not found in Ollama. Pull it using: `ollama pull {active_model}`"
                    )

                error_msg = resp.text
                try:
                    error_json = resp.json()
                    error_msg = error_json.get("error", resp.text)
                except Exception:
                    pass

                raise OllamaAPIError(
                    f"Ollama returned HTTP {resp.status_code}: {error_msg}"
                )

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise OllamaConnectionError(
                f"Cannot connect to local Ollama at {self.base_url}. Is the service running? "
                "Start it with `ollama serve` or open the Ollama desktop app."
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Ollama inference timed out after {self.read_timeout}s. "
                "The model may still be loading or generating a large token sequence."
            ) from exc
        except OllamaError:
            raise
        except Exception as exc:
            raise OllamaAPIError(f"Unexpected error communicating with Ollama: {exc}") from exc


# Shared default client instance
ollama_client = OllamaClient()
