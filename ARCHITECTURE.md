# Architecture & Roadmap

This document maps the project specification (16 sections) onto the codebase: what is implemented in Phase 1, how, and where every remaining capability will attach. The guiding principle is the spec's own: capabilities must **work together** through one pipeline, not exist as unrelated demos.

## The message pipeline

Every user message flows through one orchestrator (`backend/app/chat/service.py`):

```
user message (+ images)
        │
        ▼
┌─ build system prompt ─────────────────────────┐
│  persona (general assistant, ask-when-unsure) │
│  + long-term memories        (memory/store)   │
│  + matched skill prompts     (skills/router)  │
└───────────────────────────────────────────────┘
        │
        ▼
history trimmed to the context budget   (spec §3)
        │
        ▼
ModelProvider.chat_stream()             (providers/base)
        │                                 └─ Ollama driver today; any backend later
        ▼
streamed reply → saved to conversation
        │
        ▼
memory extraction pass (remember / forget)  → UI notice
```

Because everything passes through this pipeline, each new capability (RAG handbooks, tools, sub-agents) becomes another *stage* here — automatically combining with memory, skills, and vision instead of living beside them.

## Specification coverage

| § | Capability | Status | Where / plan |
|---|---|---|---|
| 1 | Memory (remember + forget) | ✅ Phase 1 | `memory/store.py` (SQLite, categories), `memory/extractor.py` (JSON-constrained extraction pass after each message; natural-language forget resolves to memory IDs). Memory panel for manual control. |
| 2 | Skills (modular) | ✅ Phase 1 | Skill packs = folders under `backend/skills/` (`skill.yaml` + `prompt.md`), loaded by `skills/registry.py`, routed per message by `skills/router.py` (deterministic keyword matching; router is a single function boundary so LLM routing can replace it without touching callers). Later phases extend packs with Python tool hooks (file ops, PPT generation) behind the same registry. |
| 3 | ~1M-token context target | ✅ honest handling | Context is a configurable *budget* (`context_tokens`), passed to the model as `num_ctx`; history is trimmed to fit. The API reports requested vs. model-supported vs. effective context (`/api/status`) so the 1M target is evaluated against the real model instead of assumed. A model that truly supports 1M gets 1M by raising the setting. |
| 4 | Strong / personal / fine-tuned model | ✅ Phase 1 | `providers/base.py` is a small interface (`status`, `model_info`, `chat_stream`, `chat_json`); `providers/ollama.py` implements it for any Ollama-protocol endpoint — which is how a personal or fine-tuned model connects. New protocols = new driver, zero changes elsewhere. "Updated information" (live web/search access) is planned as a skill with a tool hook once tool execution lands (Phase 3). |
| 5 | Answer questions (general) | ✅ Phase 1 | Persona in `chat/service.py` frames a general-purpose assistant; skills only *specialize* it when relevant. |
| 6 | Vision | ✅ Phase 1 | Images/screenshots attach or paste directly in the UI, stored with the message, sent base64 to the model (Ollama vision format). Optional dedicated `vision_model` setting if the main model is not multimodal. |
| 7 | Persistent UI | ✅ web / 🔜 desktop shell | Persistent web app (state survives reloads; conversations, memory, settings all server-side). Phase 4 wraps the same UI in Tauri: always-on-top window, tray icon, global hotkey — the frontend is plain HTML/JS served by the backend precisely so the shell is a thin wrapper. |
| 8 | Multimodal input (text/voice/image/screenshot) | ✅ text+image / 🔜 voice | Text, image upload, and clipboard screenshot paste work today and share one context (say "Fix this" + paste screenshot). Voice input arrives in Phase 4 as browser mic capture + a speech-to-text stage feeding the same chat pipeline. |
| 9 | Coding + cybersecurity knowledge, handbooks | ✅ skills / 🔜 RAG | Coding and Cybersecurity skill packs ship in Phase 1 (cybersecurity framed for legitimate, defensive, authorized use). Phase 2 adds a knowledge module: upload handbooks/manuals → chunk → embed → retrieve into the pipeline as a stage between memory and skills, so any skill can cite the user's own reference material. |
| 10 | Build applications (frontend+backend) | 🔜 Phase 3 | Requires tool execution (workspace, file writes, process runs). Lands together with §11 as an agentic workspace module. |
| 11 | Error recognition & iterative fixing | 🔜 Phase 3 | The PLAN→IMPLEMENT→RUN→ANALYZE→PATCH loop with a bounded iteration count, driven by the same provider interface. |
| 12 | Sub-agents | 🔜 Phase 5 | The provider abstraction + skill packs are the building blocks: a sub-agent is a scoped pipeline instance (own persona/skills/budget) coordinated by the main agent. Designed after tool execution exists, since sub-agents without tools are just prompts. |
| 13 | Computer & project interaction | 🔜 Phase 5 | Local agent capability (locate project → read files → clarify → edit → run checks → iterate → verify) built on Phase 3 tool execution, with explicit authorization gates. |
| 14 | Silent mode | 🔜 Phase 5 | Background task execution with interruptions only for clarification/authorization/completion — depends on §13's task runner; UI groundwork (task status area) precedes it. |
| 15 | Productivity capabilities (PPT, …) | 🔜 Phase 6 | Implemented as skill packs with tool hooks (e.g. a `ppt` skill generating decks), not separate apps — the skill system is already the extension point. |
| 16 | Everything works together | ✅ principle | Single pipeline (above); every phase adds stages/tools to it, never parallel systems. |

## Phases

1. **Core assistant (this phase)** — chat, memory, skills, vision, settings, dark minimal web UI.
2. **Knowledge (RAG)** — handbook/manual upload, embedding, retrieval into context; citations.
3. **Agentic workspace** — tool execution, app building, bounded run→analyze→patch loop (§10–11).
4. **Always-available & voice** — Tauri desktop shell (persistent window, tray, hotkey), voice input (§7–8 completion).
5. **Autonomy** — computer/project interaction with authorization gates, silent mode, sub-agents (§12–14).
6. **Productivity skills** — PPT creation and similar, as skill packs with tools (§15).

## Data & privacy

All state is local: SQLite + JSON under `backend/data/` (gitignored). Nothing leaves the machine except requests to the model endpoint you configure.

## Dev harness

`scripts/dev_mock_model.py` is a deliberately dumb Ollama-protocol stand-in used only where real models cannot run (CI, sandboxes). It exists so the *pipeline* is testable; it is not a feature of the assistant.
