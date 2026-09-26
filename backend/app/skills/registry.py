"""Modular skill system (spec §2).

A skill is a directory under backend/skills/ containing:

    skill.yaml   — metadata: name, description, keywords, always_on
    prompt.md    — the specialized system-prompt fragment injected when active

Skills are pure data packs: adding a capability means adding a folder, not
editing core code. Later phases can extend packs with Python hooks/tools
(file management, PPT generation, sub-agent definitions) behind the same
registry without changing the chat pipeline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config import DATA_DIR, SKILLS_DIR

_STATE_PATH = DATA_DIR / "skills_state.json"


@dataclass
class Skill:
    id: str
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    always_on: bool = False
    prompt: str = ""
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "always_on": self.always_on,
            "enabled": self.enabled,
        }


def _load_state() -> dict:
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict) -> None:
    _STATE_PATH.write_text(json.dumps(state, indent=2))


def load_skills() -> list[Skill]:
    state = _load_state()
    skills: list[Skill] = []
    if not SKILLS_DIR.is_dir():
        return skills
    for path in sorted(SKILLS_DIR.iterdir()):
        meta_path = path / "skill.yaml"
        if not meta_path.is_file():
            continue
        try:
            meta = yaml.safe_load(meta_path.read_text()) or {}
        except yaml.YAMLError:
            continue
        prompt_path = path / "prompt.md"
        skill = Skill(
            id=path.name,
            name=str(meta.get("name", path.name)),
            description=str(meta.get("description", "")),
            keywords=[str(k).lower() for k in meta.get("keywords", [])],
            always_on=bool(meta.get("always_on", False)),
            prompt=prompt_path.read_text() if prompt_path.is_file() else "",
            enabled=state.get(path.name, {}).get("enabled", True),
        )
        skills.append(skill)
    return skills


def set_enabled(skill_id: str, enabled: bool) -> bool:
    if not (SKILLS_DIR / skill_id / "skill.yaml").is_file():
        return False
    state = _load_state()
    state.setdefault(skill_id, {})["enabled"] = enabled
    _save_state(state)
    return True
