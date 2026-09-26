"""Conversation and message persistence."""
from __future__ import annotations

import json

from ..db import connection


def list_conversations() -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def create_conversation(title: str = "New conversation") -> dict:
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title) VALUES (?)", (title,)
        )
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


def delete_conversation(conversation_id: int) -> bool:
    with connection() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
        return cur.rowcount > 0


def get_messages(conversation_id: int) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, images_json, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["images"] = json.loads(item.pop("images_json") or "[]")
        out.append(item)
    return out


def add_message(
    conversation_id: int, role: str, content: str, images: list[str] | None = None
) -> int:
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, images_json) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, json.dumps(images or [])),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        return cur.lastrowid


def maybe_set_title(conversation_id: int, first_user_message: str) -> None:
    """Give a fresh conversation a title derived from its first message."""
    title = " ".join(first_user_message.split())[:60] or "New conversation"
    with connection() as conn:
        conn.execute(
            "UPDATE conversations SET title = ? "
            "WHERE id = ? AND title = 'New conversation'",
            (title, conversation_id),
        )
