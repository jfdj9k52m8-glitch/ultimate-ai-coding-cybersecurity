"""DEV-ONLY mock model server — NOT part of the assistant.

A minimal stand-in that speaks just enough of the Ollama protocol
(/api/tags, /api/show, /api/chat) to exercise the full assistant pipeline
(streaming, skill routing, memory extraction, vision plumbing) in
environments where no real model can run — e.g. CI or a sandbox.

On a real machine, run actual Ollama instead and point the assistant at it.
Every reply is clearly labeled as coming from the mock.

Usage:  python scripts/dev_mock_model.py  (listens on :11434)
"""
from __future__ import annotations

import asyncio
import json
import re

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Dev mock model")

MODEL = "dev-mock:latest"


@app.get("/api/tags")
async def tags():
    return {"models": [{"name": MODEL, "model": MODEL}]}


@app.post("/api/show")
async def show():
    return {
        "capabilities": ["completion", "vision"],
        "model_info": {"mock.context_length": 32768},
    }


def _extraction_reply(prompt: str) -> dict:
    """Heuristic remember/forget so the memory pipeline can be demoed."""
    message_match = re.search(
        r"User's latest message:\n(.*?)\n\nRespond with", prompt, re.S
    )
    message = (message_match.group(1) if message_match else "").strip()
    existing = re.findall(r"^(\d+): (.+)$", prompt, re.M)

    remember, forget_ids = [], []
    lower = message.lower()

    is_question = message.rstrip().endswith("?") or re.match(
        r"^(what|who|when|where|why|how|do|does|can|could|is|are)\b", lower
    )

    if re.search(r"\bforget\b", lower):
        target = re.sub(r".*\bforget\b(?: that)?", "", lower).strip(" .!?")
        words = set(re.findall(r"[a-z]+", target)) - {"i", "that", "the", "my", "a"}
        best_id, best_score = None, 0
        for mem_id, content in existing:
            score = len(words & set(re.findall(r"[a-z]+", content.lower())))
            if score > best_score:
                best_id, best_score = int(mem_id), score
        if best_id is not None:
            forget_ids.append(best_id)
    elif not is_question and re.search(
        r"\bremember\b|\bi prefer\b|\bi like\b|\bi'?m working on\b|\bmy name is\b|\bi use\b", lower
    ):
        content = re.sub(r"^(please\s+)?remember( that)?\s*", "", message, flags=re.I)
        content = content.strip(" .!?")
        if content:
            category = "preference" if re.search(r"\bprefer|like\b", lower) else "fact"
            if re.search(r"\bworking on|project\b", lower):
                category = "project"
            remember.append(
                {"content": re.sub(r"^i\b", "User", content, flags=re.I), "category": category}
            )

    return {"remember": remember, "forget_ids": forget_ids}


def _chat_reply(messages: list[dict]) -> str:
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    last = next(
        (m for m in reversed(messages) if m["role"] == "user"),
        {"content": "", "images": []},
    )
    image_count = len(last.get("images") or [])

    parts = [
        "**[dev-mock model]** This is a placeholder response from the development "
        "mock — connect a real Ollama model for actual intelligence.\n"
    ]
    if image_count:
        parts.append(
            f"I received **{image_count} image(s)** with your message — the vision "
            "pipeline delivered them to the model correctly. A real multimodal "
            "model would analyze their content here.\n"
        )
    if re.search(r"remember|know about me|memory", last["content"], re.I):
        mem_match = re.search(
            r"## Long-term memory\n.*?conversations:\n(.*?)(?:\n\n|$)", system, re.S
        )
        if mem_match:
            parts.append(
                "According to my long-term memory, I know this about you:\n"
                + mem_match.group(1) + "\n"
            )
        else:
            parts.append("My long-term memory about you is currently empty.\n")
    parts.append(f'Your message was: "{last["content"]}"')
    return "\n".join(parts)


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    if body.get("format") == "json":
        prompt = messages[-1]["content"] if messages else ""
        content = json.dumps(_extraction_reply(prompt))
        return JSONResponse(
            {"model": MODEL, "message": {"role": "assistant", "content": content}, "done": True}
        )

    reply = _chat_reply(messages)

    async def stream():
        for word in re.findall(r"\S+\s*", reply):
            chunk = {"model": MODEL, "message": {"role": "assistant", "content": word}, "done": False}
            yield json.dumps(chunk) + "\n"
            await asyncio.sleep(0.01)
        yield json.dumps({"model": MODEL, "message": {"role": "assistant", "content": ""}, "done": True}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=11434, log_level="warning")
