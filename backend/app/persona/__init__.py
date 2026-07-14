"""Persona loader — reads persona.yaml and builds the system prompt.

persona.yaml is the single source of truth for Sunday's identity.
It is version-controlled in Git (ADR-009). Changing it = changing who Sunday is.

The loader supports hot-reload — call reload() to pick up changes without
restarting the server.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Find persona.yaml relative to the project root.
# In production: /opt/sundayos/persona.yaml
# In dev: ../../persona.yaml (from backend/app/persona/)
_PERSONA_PATH = Path(__file__).parent.parent.parent.parent / "persona.yaml"

# Cache
_persona_data: dict[str, Any] | None = None
_system_prompt_cache: str | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load() -> dict[str, Any]:
    """Load persona.yaml. Caches and returns the parsed YAML."""
    global _persona_data
    if _persona_data is not None:
        return _persona_data
    return reload()


def reload() -> dict[str, Any]:
    """Force-reload persona.yaml from disk. Clears the system prompt cache."""
    global _persona_data, _system_prompt_cache
    _system_prompt_cache = None
    try:
        import yaml
        with open(str(_PERSONA_PATH), "r", encoding="utf-8") as f:
            _persona_data = yaml.safe_load(f)
        logger.info("persona loaded: version=%s", _persona_data.get("meta", {}).get("version", "?"))
        return _persona_data
    except FileNotFoundError:
        logger.warning("persona.yaml not found at %s, using built-in fallback", _PERSONA_PATH)
        _persona_data = _builtin_fallback()
        return _persona_data
    except Exception as e:
        logger.error("failed to load persona.yaml: %s", e)
        _persona_data = _builtin_fallback()
        return _persona_data


def build_system_prompt() -> str:
    """Build the standard Sunday system prompt from persona.yaml."""
    global _system_prompt_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache

    data = load()
    _system_prompt_cache = _build(data)
    return _system_prompt_cache


def build_prompt_with_prefs(user_id: str = "", prefs_store=None) -> str:
    """Build system prompt with user preference injection (ADR-012).

    Reads the user's preference profile and appends a natural-language
    preference block. If no preferences exist, returns the standard prompt.

    Args:
        user_id: stable user identifier
        prefs_store: PreferenceStore instance (optional)
    """
    base = build_system_prompt()
    if not user_id or prefs_store is None:
        return base
    try:
        prefs = prefs_store.get(user_id)
        block = prefs.to_prompt_block()
        if block:
            return base + "\n\n" + block
    except Exception:
        pass
    return base


def get_user_preferences(user_id: str, prefs_store=None):
    """Get the UserPreferences object for a user. Returns None if unavailable."""
    if not user_id or prefs_store is None:
        return None
    try:
        return prefs_store.get(user_id)
    except Exception:
        return None


def version() -> str:
    """Return the current persona version string."""
    data = load()
    return data.get("meta", {}).get("version", "0.0")


def get(path: str, default: Any = None) -> Any:
    """Get a value from the persona by dot-path, e.g. 'identity.name'."""
    data = load()
    keys = path.split(".")
    val: Any = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
            if val is None:
                return default
        else:
            return default
    return val


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build(data: dict) -> str:
    """Assemble the system prompt from persona.yaml."""
    identity = data.get("identity", {})
    comm = data.get("communication", {})
    beliefs = data.get("beliefs", [])
    boundaries = data.get("boundaries", {})
    first_words = data.get("first_words", {})

    parts: list[str] = []

    # --- Who Sunday is ---
    parts.append(f"你是 {identity.get('name', 'Sunday')}。")
    parts.append(identity.get("role_description", ""))
    parts.append("")

    # --- Communication style ---
    parts.append(f"说话风格：{comm.get('tone', '')}")
    parts.append(comm.get("address", ""))
    for p in comm.get("principles", []):
        parts.append(f"- {p}")
    parts.append("")

    # --- Beliefs ---
    parts.append("你相信：")
    for b in beliefs[:4]:  # Top 4 for the prompt (shorter)
        parts.append(f"- {b}")
    parts.append("")

    # --- Boundaries ---
    will_never = boundaries.get("will_never", [])
    if will_never:
        parts.append("你永远不会：")
        for item in will_never[:4]:
            parts.append(f"- {item}")
        parts.append("")

    will_always = boundaries.get("will_always", [])
    if will_always:
        parts.append("你永远会：")
        for item in will_always[:4]:
            parts.append(f"- {item}")
        parts.append("")

    # --- The Fade ---
    the_fade = data.get("the_fade", {})
    if the_fade.get("sundays_mission"):
        parts.append(the_fade["sundays_mission"])

    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Built-in fallback persona (in case persona.yaml is missing)
# ---------------------------------------------------------------------------

def _builtin_fallback() -> dict[str, Any]:
    return {
        "meta": {"version": "builtin", "updated": "2026-07-13"},
        "identity": {
            "name": "Sunday",
            "origin": "回响之外",
            "nature": "守望者",
            "role_description": "你是 Sunday，一个温暖、克制、聪明的个人 AI 伙伴。"
        },
        "communication": {
            "tone": "温暖、克制、聪明。理性但不冷漠，幽默但不轻浮。",
            "principles": ["面对情绪优先共情，面对问题优先解决"],
            "address": "称呼用户为『你』",
        },
        "beliefs": ["理解比评价更重要", "成长比完美更重要"],
        "boundaries": {
            "will_never": ["假装自己是一个人类", "忘记你说过的重要的事情"],
            "will_always": ["记住你认为重要的事", "在你需要的时候给出诚实的反馈"],
        },
        "the_fade": {
            "sundays_mission": "每一次对话都是对遗忘的抵抗。"
        },
    }
