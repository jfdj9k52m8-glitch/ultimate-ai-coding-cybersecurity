"""Automatic memory extraction (spec §1).

After each user message the model is asked — in a separate, JSON-constrained
call — whether anything durable should be remembered or forgotten. Failures
are silent by design: memory extraction must never break the chat flow.
"""
from __future__ import annotations

from ..providers.base import ChatMessage, ModelProvider
from . import store

_EXTRACTION_PROMPT = """You maintain the long-term memory of a personal AI assistant.

Analyze ONLY the user's latest message below and decide:
1. "remember": a list of NEW durable items worth storing long-term, each as
   {{"content": "...", "category": "preference|fact|project|task|other"}}.
   Only store genuinely durable information: user preferences, facts the user
   states about themselves, their projects, or ongoing tasks.
   Do NOT store one-off questions, greetings, or requests that carry no
   lasting information. Most messages contain nothing to remember — an empty
   list is the normal answer. Write each item as a short third-person
   statement, e.g. "User prefers dark minimal interfaces."
2. "forget_ids": IDs of existing memories the user explicitly asked to forget
   or that this message directly contradicts. Empty list if none.

Existing memories:
{existing}

User's latest message:
{message}

Respond with ONLY this JSON object:
{{"remember": [{{"content": "...", "category": "..."}}], "forget_ids": []}}"""


async def extract_and_apply(
    provider: ModelProvider, model: str, user_message: str
) -> dict:
    """Run extraction on a user message and apply the result.

    Returns {"remembered": [...], "forgotten": [...]} describing what changed.
    """
    result = {"remembered": [], "forgotten": []}
    if not user_message.strip():
        return result

    existing = store.list_memories()
    existing_text = (
        "\n".join(f'{m["id"]}: {m["content"]}' for m in existing) or "(none)"
    )
    prompt = _EXTRACTION_PROMPT.format(existing=existing_text, message=user_message)

    data = await provider.chat_json(
        model, [ChatMessage(role="user", content=prompt)]
    )
    if not isinstance(data, dict):
        return result

    for item in data.get("remember") or []:
        if isinstance(item, str):
            item = {"content": item, "category": "other"}
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        saved = store.add_memory(content, str(item.get("category", "other")))
        if not saved.get("duplicate"):
            result["remembered"].append(saved)

    valid_ids = {m["id"] for m in existing}
    for memory_id in data.get("forget_ids") or []:
        try:
            memory_id = int(memory_id)
        except (TypeError, ValueError):
            continue
        if memory_id in valid_ids and store.delete_memory(memory_id):
            forgotten = next(m for m in existing if m["id"] == memory_id)
            result["forgotten"].append(forgotten)

    return result
