"""Long-term memory store (spec §1).

Memories persist across conversations in SQLite. They can be created
automatically (extractor), added manually, and deleted — either explicitly
from the UI or through a natural-language "forget ..." request.
"""
from __future__ import annotations

from ..db import connection

CATEGORIES = ("preference", "fact", "project", "task", "other")


def list_memories() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, content, category, created_at FROM memories ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def add_memory(content: str, category: str = "fact") -> dict:
    content = content.strip()
    if category not in CATEGORIES:
        category = "other"
    with connection() as conn:
        # Skip near-duplicates.
        existing = conn.execute(
            "SELECT id FROM memories WHERE lower(content) = lower(?)", (content,)
        ).fetchone()
        if existing:
            return {"id": existing["id"], "content": content, "category": category, "duplicate": True}
        cur = conn.execute(
            "INSERT INTO memories (content, category) VALUES (?, ?)",
            (content, category),
        )
        return {"id": cur.lastrowid, "content": content, "category": category}


def delete_memory(memory_id: int) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        return cur.rowcount > 0


def memory_block(max_chars: int = 4000) -> str:
    """Render memories for injection into the system prompt."""
    memories = list_memories()
    if not memories:
        return ""
    lines, used = [], 0
    for m in memories:
        line = f"- ({m['category']}) {m['content']}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)
