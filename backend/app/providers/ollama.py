"""Ollama-protocol provider.

Works with a local Ollama instance or any endpoint speaking the Ollama API,
which is how a personal/fine-tuned multimodal model is expected to be
connected (spec §4). Images are passed as base64 per the Ollama chat API,
covering vision (spec §6) when the underlying model is multimodal.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx

from .base import ChatMessage, ModelProvider, ProviderStatus


class OllamaProvider(ModelProvider):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _payload_messages(self, messages: list[ChatMessage]) -> list[dict]:
        out = []
        for m in messages:
            item: dict = {"role": m.role, "content": m.content}
            if m.images:
                item["images"] = m.images
            out.append(item)
        return out

    async def status(self) -> ProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return ProviderStatus(reachable=True, models=models)
        except Exception as exc:  # noqa: BLE001 — surface any connectivity issue
            return ProviderStatus(reachable=False, models=[], detail=str(exc))

    async def model_info(self, model: str) -> dict:
        """Return {"max_context": int | None, "capabilities": [...]}."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self.base_url}/api/show", json={"model": model}
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:  # noqa: BLE001
            return {"max_context": None, "capabilities": []}

        max_context = None
        for key, value in (data.get("model_info") or {}).items():
            if key.endswith(".context_length"):
                max_context = value
                break
        return {
            "max_context": max_context,
            "capabilities": data.get("capabilities", []),
        }

    async def chat_stream(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        context_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": self._payload_messages(messages),
            "stream": True,
            "options": {"num_ctx": context_tokens, "temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10)) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise RuntimeError(chunk["error"])
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        return

    async def chat_json(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.0,
    ) -> Optional[dict]:
        payload = {
            "model": model,
            "messages": self._payload_messages(messages),
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                content = resp.json().get("message", {}).get("content", "")
                return json.loads(content)
        except Exception:  # noqa: BLE001 — extraction must never break chat
            return None


def get_provider(settings: dict) -> ModelProvider:
    # Single registry point: new provider types (spec §4 — stronger or
    # fine-tuned models behind other protocols) are added here.
    return OllamaProvider(settings["base_url"])
