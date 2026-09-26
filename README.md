# Personal AI Assistant

A highly customizable personal AI assistant — Phase 1 of the [project specification](./ARCHITECTURE.md#specification-coverage).

**Working now (Phase 1):**

- **Chat & Q&A** — general-purpose assistant with streamed Markdown responses and persistent conversation history.
- **Long-term memory** — remembers preferences, facts, projects and tasks across conversations, automatically extracted from what you say. Supports natural-language *forget* ("Forget that I prefer dark interfaces") plus a Memory panel for manual add/remove.
- **Modular skills** — capability packs (Coding, Cybersecurity, Research, File management) that activate automatically when a message matches them. Each skill is a self-contained folder; drop in a new folder to add a skill.
- **Vision** — attach images or paste screenshots directly into the chat; they are forwarded to the (multimodal) model.
- **Model-agnostic** — talks to any Ollama-compatible endpoint: local Ollama, a self-hosted personal model, or a future fine-tuned one. Context window is configurable and honestly reported (requested vs. what the model actually supports).
- **Dark, minimal web UI** — served by the backend on one port; architected to be wrapped in a desktop shell (Tauri/Electron) in a later phase for an always-available persistent window.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design and the roadmap covering the rest of the specification (sub-agents, agentic build-and-fix loop, voice, silent mode, RAG handbooks, …).

## Running it

Prerequisites: Python 3.11+, Node 20+, and [Ollama](https://ollama.com) (or any endpoint speaking the Ollama API) with at least one model pulled — ideally a multimodal one, e.g.:

```bash
ollama pull qwen2.5vl        # or any model you prefer
```

Build the UI once, then start the server:

```bash
# 1. Frontend
cd frontend
npm install
npm run build

# 2. Backend (serves API + UI on one port)
cd ../backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000, go to **Settings**, pick your model, and chat.

### Configuration

Everything is editable in the **Settings** panel at runtime. Initial defaults can come from the environment:

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama-compatible endpoint |
| `ASSISTANT_MODEL` | *(empty)* | Main chat model |
| `ASSISTANT_VISION_MODEL` | *(empty)* | Optional dedicated vision model; empty = main model handles images |
| `ASSISTANT_CONTEXT_TOKENS` | `32768` | Requested context window (see §3 of the spec — the effective value is capped at what the model truly supports and shown in Settings) |
| `ASSISTANT_DATA_DIR` | `backend/data` | Where memory/conversations/settings persist |

### Development

```bash
# backend with reload
cd backend && python -m uvicorn app.main:app --reload --port 8000
# frontend dev server (proxies /api to :8000)
cd frontend && npm run dev
```

No real model available (CI/sandbox)? A **dev-only mock** that speaks the Ollama protocol lets you exercise the whole pipeline — streaming, skills, memory extraction, vision plumbing:

```bash
python scripts/dev_mock_model.py   # listens on :11434, model "dev-mock:latest"
```

It is a test harness, not part of the assistant; every reply is labeled as mock output.

## Adding a skill

Create `backend/skills/<skill-id>/` with two files:

```yaml
# skill.yaml
name: My skill
description: What this capability is for.
always_on: false        # true = active on every message
keywords: [word, that, triggers, it]
```

```markdown
<!-- prompt.md -->
Instructions injected into the system prompt when this skill is active.
```

Restart the server; the skill appears in the Skills panel.

## Project layout

```
backend/
  app/
    providers/   # model abstraction (Ollama driver; new backends plug in here)
    memory/      # long-term memory store + automatic extraction
    skills/      # skill registry + routing
    chat/        # orchestration: memory + skills + history + vision → model
    api/         # HTTP/SSE API
  skills/        # skill packs (data, not code)
  data/          # runtime state: SQLite DB, settings (gitignored)
frontend/        # React UI (dark, minimal)
scripts/         # dev utilities (mock model server)
```
