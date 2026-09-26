"""Model provider abstraction.

The assistant is model-agnostic by design (spec §4): any backend that can
implement this interface — a local Ollama instance, a self-hosted personal
model, a future fine-tuned model — can power the assistant without touching
the rest of the codebase.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str
    images: list[str] = field(default_factory=list)  # base64-encoded images


@dataclass
class ProviderStatus:
    reachable: bool
    models: list[str]
    detail: str = ""


class ModelProvider(ABC):
    """Interface every model backend must implement."""

    @abstractmethod
    async def status(self) -> ProviderStatus:
        """Health check: is the backend reachable, which models exist."""

    @abstractmethod
    async def model_info(self, model: str) -> dict:
        """Metadata for a model (e.g. real max context length, vision capability)."""

    @abstractmethod
    async def chat_stream(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        context_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream assistant response tokens."""

    @abstractmethod
    async def chat_json(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
    ) -> Optional[dict]:
        """Single non-streamed completion constrained to JSON (used for
        memory extraction). Returns None on failure — callers must degrade
        gracefully."""
