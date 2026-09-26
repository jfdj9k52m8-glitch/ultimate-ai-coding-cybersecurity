"""HTTP API for the assistant UI."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import config
from ..chat import conversations, service
from ..memory import store as memory_store
from ..providers.ollama import get_provider
from ..skills.registry import load_skills, set_enabled

router = APIRouter(prefix="/api")


# --- Status & settings -----------------------------------------------------

@router.get("/status")
async def status():
    settings = config.load_settings()
    provider = get_provider(settings)
    provider_status = await provider.status()

    model_info = {"max_context": None, "capabilities": []}
    if provider_status.reachable and settings["model"]:
        model_info = await provider.model_info(settings["model"])

    # Honest 1M-context reporting (spec §3): what was requested vs. what the
    # actual model supports.
    max_context = model_info["max_context"]
    return {
        "provider": settings["provider"],
        "base_url": settings["base_url"],
        "reachable": provider_status.reachable,
        "detail": provider_status.detail,
        "available_models": provider_status.models,
        "model": settings["model"],
        "vision_model": settings["vision_model"],
        "requested_context_tokens": settings["context_tokens"],
        "model_max_context": max_context,
        "effective_context_tokens": (
            min(settings["context_tokens"], max_context)
            if max_context
            else settings["context_tokens"]
        ),
        "capabilities": model_info["capabilities"],
    }


class SettingsUpdate(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    vision_model: Optional[str] = None
    context_tokens: Optional[int] = Field(default=None, ge=2048)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    memory_extraction: Optional[bool] = None


@router.get("/settings")
async def get_settings():
    return config.load_settings()


@router.put("/settings")
async def update_settings(update: SettingsUpdate):
    return config.save_settings(update.model_dump(exclude_none=True))


# --- Conversations ----------------------------------------------------------

@router.get("/conversations")
async def get_conversations():
    return conversations.list_conversations()


@router.post("/conversations")
async def new_conversation():
    return conversations.create_conversation()


@router.delete("/conversations/{conversation_id}")
async def remove_conversation(conversation_id: int):
    if not conversations.delete_conversation(conversation_id):
        raise HTTPException(404, "Conversation not found")
    return {"ok": True}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int):
    return conversations.get_messages(conversation_id)


# --- Chat (SSE stream) -------------------------------------------------------

class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str
    images: list[str] = Field(default_factory=list)  # base64 (no data: prefix)


@router.post("/chat")
async def chat(request: ChatRequest):
    settings = config.load_settings()
    provider = get_provider(settings)

    if not settings["model"]:
        raise HTTPException(
            409,
            "No model configured. Open Settings and select a model "
            "from your Ollama-compatible endpoint.",
        )

    conversation_id = request.conversation_id
    if conversation_id is None:
        conversation_id = conversations.create_conversation()["id"]

    async def event_stream():
        yield _sse({"type": "conversation", "id": conversation_id})
        async for event in service.run_chat(
            provider, settings, conversation_id, request.message, request.images
        ):
            yield _sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# --- Memory ------------------------------------------------------------------

class MemoryCreate(BaseModel):
    content: str
    category: str = "fact"


@router.get("/memories")
async def get_memories():
    return memory_store.list_memories()


@router.post("/memories")
async def add_memory(memory: MemoryCreate):
    if not memory.content.strip():
        raise HTTPException(422, "Memory content cannot be empty")
    return memory_store.add_memory(memory.content, memory.category)


@router.delete("/memories/{memory_id}")
async def forget_memory(memory_id: int):
    if not memory_store.delete_memory(memory_id):
        raise HTTPException(404, "Memory not found")
    return {"ok": True}


# --- Skills ------------------------------------------------------------------

@router.get("/skills")
async def get_skills():
    return [s.to_dict() for s in load_skills()]


class SkillToggle(BaseModel):
    enabled: bool


@router.put("/skills/{skill_id}")
async def toggle_skill(skill_id: str, toggle: SkillToggle):
    if not set_enabled(skill_id, toggle.enabled):
        raise HTTPException(404, "Skill not found")
    return {"ok": True}
