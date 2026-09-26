"""Runtime configuration.

Defaults come from environment variables; user-editable settings are
persisted to data/settings.json so they survive restarts.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = Path(os.environ.get("ASSISTANT_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SKILLS_DIR = Path(os.environ.get("ASSISTANT_SKILLS_DIR", BASE_DIR / "skills"))
DB_PATH = DATA_DIR / "assistant.db"
SETTINGS_PATH = DATA_DIR / "settings.json"

_DEFAULTS = {
    # Any Ollama-compatible endpoint. A personal/self-hosted model served
    # through Ollama (or an API that speaks the Ollama protocol) plugs in here.
    "provider": "ollama",
    "base_url": os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    # Main chat model. If it is multimodal, images are sent to it directly.
    "model": os.environ.get("ASSISTANT_MODEL", ""),
    # Optional dedicated vision model. Empty = use the main model for images.
    "vision_model": os.environ.get("ASSISTANT_VISION_MODEL", ""),
    # Requested context window (tokens). The 1M target from the spec is a
    # *target*: we request min(this, what the model actually supports) and
    # surface the real number in /api/status so it can be evaluated honestly.
    "context_tokens": int(os.environ.get("ASSISTANT_CONTEXT_TOKENS", "32768")),
    "temperature": 0.7,
    # Automatic memory extraction after each user message.
    "memory_extraction": True,
}

_lock = threading.Lock()


def load_settings() -> dict:
    settings = dict(_DEFAULTS)
    if SETTINGS_PATH.exists():
        try:
            settings.update(json.loads(SETTINGS_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_settings(updates: dict) -> dict:
    with _lock:
        settings = load_settings()
        for key, value in updates.items():
            if key in _DEFAULTS and value is not None:
                settings[key] = value
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    return settings
