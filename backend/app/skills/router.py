"""Skill routing: decide which skills apply to a given message.

Phase 1 uses deterministic keyword matching — it is transparent, fast, and
works with any model. The router is a single function boundary, so a later
phase can swap in LLM-based routing without touching callers.
"""
from __future__ import annotations

import re

from .registry import Skill


def select_skills(skills: list[Skill], user_message: str) -> list[Skill]:
    text = user_message.lower()
    selected: list[Skill] = []
    for skill in skills:
        if not skill.enabled:
            continue
        if skill.always_on:
            selected.append(skill)
            continue
        for keyword in skill.keywords:
            # Whole-word match so "css" doesn't fire on "access".
            if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text):
                selected.append(skill)
                break
    return selected
