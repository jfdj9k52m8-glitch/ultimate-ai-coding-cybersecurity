"""Chat orchestration.

This is where the spec's capabilities converge for each message:

  memory (§1)  → remembered facts injected into the system prompt
  skills (§2)  → matching skill prompts activated for this message
  context (§3) → history trimmed to an explicit token budget
  Q&A (§5)     → general-assistant persona, not only coding
  vision (§6)  → attached images forwarded to the (multimodal) model
"""
from __future__ import annotations

from typing import AsyncIterator

from ..memory import store as memory_store
from ..memory.extractor import extract_and_apply
from ..providers.base import ChatMessage, ModelProvider
from ..skills.registry import load_skills
from ..skills.router import select_skills
from . import conversations

_PERSONA = """You are a personal AI assistant — a general-purpose assistant, \
not only a coding tool. You answer questions, explain concepts, analyze \
images and screenshots, and help with the user's projects.

Principles:
- Understand the task before acting; when a request is genuinely ambiguous, \
ask a focused clarifying question instead of guessing.
- Use your long-term memory of the user naturally, without announcing it.
- Be direct and concise; use Markdown formatting when it helps.
- If an image or screenshot is attached, examine it carefully and ground \
your answer in what it actually shows."""


def _approx_tokens(text: str) -> int:
    # Heuristic: ~4 characters per token. Good enough for budgeting.
    return max(1, len(text) // 4)


def build_system_prompt(user_message: str) -> tuple[str, list[str]]:
    """Compose persona + memories + matched skill prompts."""
    parts = [_PERSONA]

    memories = memory_store.memory_block()
    if memories:
        parts.append(
            "## Long-term memory\n"
            "Things you remember about the user from previous conversations:\n"
            + memories
        )

    active = select_skills(load_skills(), user_message)
    for skill in active:
        parts.append(skill.prompt.strip())

    return "\n\n".join(parts), [s.name for s in active]


def build_messages(
    conversation_id: int,
    user_message: str,
    images: list[str],
    *,
    context_tokens: int,
) -> tuple[list[ChatMessage], list[str]]:
    """Assemble the request within the context budget (spec §3).

    Newest history is kept; oldest turns are dropped once the budget —
    the configured context window minus a reply reserve — is exhausted.
    """
    system_prompt, active_skills = build_system_prompt(user_message)

    budget = max(2048, context_tokens - 1024)  # reserve room for the reply
    budget -= _approx_tokens(system_prompt) + _approx_tokens(user_message)

    history: list[ChatMessage] = []
    for msg in reversed(conversations.get_messages(conversation_id)):
        cost = _approx_tokens(msg["content"]) + 768 * len(msg["images"])
        if budget - cost < 0:
            break
        budget -= cost
        history.append(
            ChatMessage(role=msg["role"], content=msg["content"], images=msg["images"])
        )
    history.reverse()

    messages = [ChatMessage(role="system", content=system_prompt)]
    messages.extend(history)
    messages.append(ChatMessage(role="user", content=user_message, images=images))
    return messages, active_skills


async def run_chat(
    provider: ModelProvider,
    settings: dict,
    conversation_id: int,
    user_message: str,
    images: list[str],
) -> AsyncIterator[dict]:
    """Yield SSE-ready events: meta → token* → (memory?) → done | error."""
    conversations.maybe_set_title(conversation_id, user_message)

    messages, active_skills = build_messages(
        conversation_id, user_message, images,
        context_tokens=settings["context_tokens"],
    )
    conversations.add_message(conversation_id, "user", user_message, images)

    # A dedicated vision model (if configured) handles image turns; otherwise
    # the main model receives images directly (personal model assumed multimodal).
    model = settings["model"]
    if images and settings.get("vision_model"):
        model = settings["vision_model"]

    yield {"type": "meta", "skills": active_skills, "model": model}

    reply_parts: list[str] = []
    try:
        async for token in provider.chat_stream(
            model,
            messages,
            context_tokens=settings["context_tokens"],
            temperature=settings["temperature"],
        ):
            reply_parts.append(token)
            yield {"type": "token", "content": token}
    except Exception as exc:  # noqa: BLE001 — report, don't crash the stream
        yield {"type": "error", "message": f"Model error: {exc}"}
        if not reply_parts:
            return

    reply = "".join(reply_parts)
    if reply:
        conversations.add_message(conversation_id, "assistant", reply)

    memory_updates = None
    if settings.get("memory_extraction") and settings["model"]:
        updates = await extract_and_apply(provider, settings["model"], user_message)
        if updates["remembered"] or updates["forgotten"]:
            memory_updates = updates
            yield {"type": "memory", **updates}

    yield {"type": "done", "memory": memory_updates}
