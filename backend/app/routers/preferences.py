"""Feedback & Preferences API endpoints (ADR-012).

Three routes: get preferences, post feedback, update preferences.
"""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from ..deps import ctx, get_current_user
from ..persona import get_user_preferences
from ..persona.feedback_parser import parse_feedback

router = APIRouter(tags=["preferences"])


class FeedbackRequest(BaseModel):
    rating: int  # 1 = 👍, -1 = 👎
    feedback_text: str = ""
    engine_id: str = ""
    msg_preview: str = ""  # first 60 chars of the AI reply


@router.get("/api/preferences")
async def get_prefs(user_id: str = Depends(get_current_user)) -> dict:
    """Return the current user's preference profile."""
    prefs = get_user_preferences(user_id, ctx.pref_store)
    return {
        "user_id": user_id,
        "style": prefs.style if prefs else "",
        "topics": prefs.topics if prefs else {},
        "history": prefs.history[-10:] if prefs else [],
    }


@router.post("/api/feedback")
async def post_feedback(req: FeedbackRequest,
                        user_id: str = Depends(get_current_user)) -> dict:
    """Submit feedback on a reply. Adjusts quality score and parses NL feedback."""

    # 1. Adjust engine quality (immediate, lightweight)
    if req.engine_id:
        for e in ctx.engines:
            if e.id == req.engine_id:
                delta = 0.01 if req.rating > 0 else -0.02
                e.caps.quality = max(0.1, min(1.0, e.caps.quality + delta))
                break

    # 2. Parse natural-language feedback (async, optional)
    parsed = {}
    if req.feedback_text.strip():
        try:
            parsed = await parse_feedback(req.feedback_text, ctx.router)
            # Apply parsed preferences
            if parsed.get("action") in ("prompt_inject", "both"):
                prefs = ctx.pref_store.get(user_id)
                if parsed.get("dimension") == "style" and parsed.get("style_value"):
                    prefs.style = parsed["summary"]
                if parsed.get("dimension") == "topic" and parsed.get("topic_preference"):
                    prefs.topics[parsed["topic"]] = parsed["topic_preference"]
                prefs.add_feedback(req.feedback_text, req.rating,
                                  req.engine_id, parsed.get("summary", ""))
                ctx.pref_store.save(prefs)
        except Exception:
            pass  # NL parsing is best-effort; never block feedback

    # 3. Log to feedback_log (best-effort, don't crash on DB errors)
    try:
        ctx.pref_store.log_feedback(
            user_id, req.msg_preview, req.engine_id,
            req.rating, req.feedback_text, parsed)
    except Exception:
        pass

    return {
        "rating": req.rating,
        "engine_adjusted": req.engine_id,
        "parsed_feedback": parsed,
    }


@router.post("/api/preferences/update")
async def update_prefs(body: Dict[str, Any],
                       user_id: str = Depends(get_current_user)) -> dict:
    """Directly set a preference value via API (for settings UI)."""
    prefs = ctx.pref_store.get(user_id)

    if "style" in body:
        prefs.style = body["style"]
    if "topic_prefs" in body:
        for topic, pref in body["topic_prefs"].items():
            prefs.topics[topic] = pref
    if "engine_prefs" in body:
        prefs.engine_prefs.update(body["engine_prefs"])

    ctx.pref_store.save(prefs)
    return {"user_id": user_id, "style": prefs.style, "topics": prefs.topics}
