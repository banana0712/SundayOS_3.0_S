"""Chat router — main chat endpoints (non-streaming and streaming)."""
from __future__ import annotations

import json as _json
import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..deps import get_current_user, ctx
from ..log_engine import log
from ..engines.base import EngineMessage, Complexity
from ..engines.router import CognitiveRequest
from ..memory.schema import MemoryNode, MemoryType
from ..memory.reflection import schedule_reflection
from ..memory.importance import score_importance
from ..cognition.context_builder import build_context
from ..cognition.dispatch import needs_reasoner, risk_level, BeliefState
from ..cognition.react_loop import ReActLoop
from ..cognition.burst_split import burst_split
from ..cognition.context_window import manage_context_window, build_context_with_window
from ..persona import build_prompt_with_prefs
from ..persona.empathy import run_empathy_pipeline
from ..guardrails.pipeline import check_input, GuardrailTripwire
from ..guardrails.pii import redact_pii

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..deps import _Context

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    role_hint: str | None = None
    voice_input: bool = False


def _get_recent_topics(conv_id: str, limit: int = 3) -> list[str]:
    """从最近对话中提取话题关键词（简单规则）"""
    if not conv_id:
        return []

    conv = ctx.conversations.get(conv_id)
    if not conv or not conv.messages:
        return []

    # 提取最近几条用户消息的关键词
    topics = []
    user_messages = [m for m in conv.messages[-6:] if m.get("role") == "user"]

    for msg in user_messages[-limit:]:
        # 简单规则：提取常见话题词
        content = msg.get("content", "").lower()
        topic_keywords = {
            "运动": ["跑步", "健身", "运动", "游泳"],
            "工作": ["工作", "项目", "会议", "代码"],
            "学习": ["学", "课程", "考试", "书"],
            "健康": ["生病", "医院", "药", "健康"],
            "旅行": ["旅行", "机票", "酒店"],
        }
        for topic, keywords in topic_keywords.items():
            if any(kw in content for kw in keywords):
                if topic not in topics:
                    topics.append(topic)

    return topics[:limit]


def _record_stats(engine_id: str | None, latency_ms: float,
                  prompt_tokens: int, completion_tokens: int, cost_usd: float,
                  event: str = "") -> None:
    ctx.runtime.record_call(engine_id, latency_ms, prompt_tokens, completion_tokens, cost_usd, event)


@router.post("")
async def chat(req: ChatRequest, user_id: str = Depends(get_current_user)) -> dict:
    """Main chat endpoint — non-streaming."""

    # Debug: write to file
    with open("/tmp/sunday_debug.log", "a") as f:
        f.write(f"[CHAT_ENTRY] message={req.message[:50]}, conv_id={req.conversation_id}\n")
    print(f"[CHAT_ENTRY] Received message: {req.message[:50]}, conv_id: {req.conversation_id}", flush=True)

    # 生成 request_id 用于追踪整个交互流程
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    session_id = req.conversation_id or "new_session"

    # 记录交互开始
    log.interaction_start(
        session_id=session_id,
        user_id=user_id,
        request_id=request_id,
        user_message=req.message,
        conversation_id=req.conversation_id,
        metadata={"role_hint": req.role_hint}
    )

    # L6 input guardrails
    try:
        check_input(req.message)
        log.guardrail_check(request_id, "input", True, "all checks passed")
    except GuardrailTripwire as t:
        log.guardrail_check(request_id, "input", False, f"{t.layer}:{t.reason}")
        raise HTTPException(status_code=400, detail=f"guardrail:{t.layer}:{t.reason}")

    # Build topic-aware cross-session context (Engram/GAM/APEX-MEM)
    recent_topics = _get_recent_topics(req.conversation_id)
    assembled = await build_context(req.message, user_id, ctx.memory, ctx.router, recent_topics=recent_topics)
    context_block = assembled.to_prompt_section() if assembled else ""

    # Get conversation history (may already be compressed from previous turns)
    conversation_messages = []
    if req.conversation_id:
        conv = ctx.conversations.get(req.conversation_id)
        if conv and conv.messages:
            conversation_messages = conv.messages

    # 记录上下文检索
    if assembled:
        log.context_retrieved(
            request_id=request_id,
            memory_nodes=[],
            conversation_history=[],
            retrieved_count=len(assembled.topic_history.split('\n')) if assembled.topic_history else 0
        )

    # Empathy: UU analysis → IRG guidance
    empathy_snapshot, empathy_guidance = await run_empathy_pipeline(
        req.message, ctx.router,
    )

    # Check for conversation history summary
    conv_summary = None
    if req.conversation_id:
        conv = ctx.conversations.get(req.conversation_id)
        if conv and hasattr(conv, 'summary') and conv.summary:
            conv_summary = conv.summary

    # Dispatch: System 1 vs System 2
    belief = BeliefState(user_id=user_id)
    use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)
    complexity = Complexity.L3_DEEP if use_reasoner else Complexity.L2_DAILY

    system_prompt = build_prompt_with_prefs(user_id, ctx.pref_store)
    if conv_summary:
        system_prompt += f"\n\n[对话历史摘要]\n{conv_summary}"
    if empathy_guidance:
        system_prompt += f"\n\n[当前互动]\n{empathy_guidance}"
    if context_block:
        system_prompt += f"\n\n{context_block}"

    react_steps = []
    log.chat_request(user_id, len(req.message),
                     "reasoner" if use_reasoner else "talker",
                     int(complexity))

    if use_reasoner:
        # System 2: ReAct loop — Thought → Action → Observation
        react = ReActLoop(router=ctx.router, tools=ctx.tools, memory_store=ctx.memory, skills=ctx.skills,
                          max_steps=7, timeout_s=120.0)
        react_result = await react.run(
            system_prompt=system_prompt,
            user_message=req.message,
            user_id=user_id,
        )
        reply = react_result.answer
        react_steps = [
            {
                "type": s.type, "content": s.content,
                "tool_name": s.tool_name, "tool_input": s.tool_input,
                "tool_output": s.tool_output, "latency_ms": s.latency_ms,
            }
            for s in react_result.steps
        ]
        # Use a synthetic trace for the ReAct run
        trace = {
            "candidates": [], "scores": {}, "reason": "react_loop",
            "fallbacks_used": [], "usage": {}, "latency_ms": react_result.total_latency_ms,
            "errors": {},
        }
        chosen_engine = "react-loop"
    else:
        # System 1: single completion with conversation history
        messages = [
            EngineMessage(role="system", content=system_prompt),
        ]

        # Add compressed conversation history if available
        if conversation_messages:
            for msg in conversation_messages:
                # Ensure msg is a dict
                if not isinstance(msg, dict):
                    continue
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Skip system messages from compression (already in system_prompt)
                if role == "system":
                    # System message from compression summary - add to system prompt
                    system_prompt += f"\n\n{content}"
                    continue
                # Only add user/assistant messages
                if role in ("user", "assistant"):
                    messages.append(EngineMessage(role=role, content=content))

        # Add current user message
        messages.append(EngineMessage(role="user", content=req.message))

        # Pre-route log: what the router sees
        ranked, plan_trace = ctx.router.plan(CognitiveRequest(
            messages=messages, complexity=complexity, prefer_chinese=True))
        log.route_decision(int(complexity), plan_trace.candidates,
                          plan_trace.scores, plan_trace.chosen,
                          plan_trace.reason, req.message)

        result = await ctx.router.route(CognitiveRequest(
            messages=messages,
            complexity=complexity,
            prefer_chinese=True,
        ))

        if result.response is None:
            errors = result.trace.errors
            log.chat_all_engines_failed(user_id, errors)
            if errors:
                first_err = next(iter(errors.values()))
                reply = "引擎暂时不可用，请稍后重试。"
            else:
                reply = "引擎暂时不可用，请稍后重试。"
        else:
            reply, _ = redact_pii(result.response.text)

        trace = {
            "candidates": result.trace.candidates,
            "scores": result.trace.scores,
            "reason": result.trace.reason,
            "fallbacks_used": result.trace.fallbacks_used,
            "usage": result.trace.usage,
            "latency_ms": result.trace.latency_ms,
            "errors": result.trace.errors,
        }
        chosen_engine = result.trace.chosen or "none"

        # Post-route log: what actually happened
        log.chat_response(user_id, chosen_engine,
                         trace.get("latency_ms", 0), len(reply or ""),
                         trace.get("usage", {}).get("prompt_tokens", 0) +
                         trace.get("usage", {}).get("completion_tokens", 0),
                         trace.get("usage", {}).get("cost_usd", 0))

    # Record usage stats
    if use_reasoner:
        _record_stats("react-loop", react_result.total_latency_ms, 0, 0, 0,
                      event=f"ReAct: {len(react_steps)} steps → {reply[:50]}...")
    else:
        latency = trace.get("latency_ms", 0)
        usage = trace.get("usage", {})
        _record_stats(chosen_engine, latency,
                      usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                      usage.get("cost_usd", 0),
                      event=f"{chosen_engine} · {req.message[:40]}")

    # --- conversation session: auto-create or append ---
    conv_id = req.conversation_id
    if not conv_id or not ctx.conversations.get(conv_id):
        conv = ctx.conversations.create(user_id)
        conv_id = conv.id

    print(f"[BEFORE ADD] conv_id={conv_id}, msg_count={len(ctx.conversations.get(conv_id).messages)}", flush=True)
    with open("/tmp/sunday_debug.log", "a") as f:
        f.write(f"[BEFORE] {conv_id} {len(ctx.conversations.get(conv_id).messages)}\n")

    ctx.conversations.add_message(conv_id, "user", req.message)
    ctx.conversations.add_message(conv_id, "assistant", reply,
                     engine=chosen_engine,
                     system="reasoner" if use_reasoner else "talker",
                     trace={
                         "engine": chosen_engine,
                         "system": "reasoner" if use_reasoner else "talker",
                         "complexity": int(complexity),
                         "errors": trace.get("errors", {}),
                         "latency_ms": trace.get("latency_ms", 0),
                         "react_steps": react_steps,
                     })

    print(f"[AFTER ADD] conv_id={conv_id}, msg_count={len(ctx.conversations.get(conv_id).messages)}", flush=True)
    with open("/tmp/sunday_debug.log", "a") as f:
        f.write(f"[AFTER] {conv_id} {len(ctx.conversations.get(conv_id).messages)}\n")

    # Apply context window management after adding new messages
    conv = ctx.conversations.get(conv_id)
    msg_count = len(conv.messages) if conv else 0
    print(f"[COMPRESSION_CHECK] conv_id={conv_id}, messages={msg_count}, threshold=12", flush=True)
    logger.info(f"[COMPRESSION_CHECK] conv_id={conv_id}, messages={msg_count}, threshold=12")
    with open("/tmp/sunday_debug.log", "a") as f:
        f.write(f"[CHECK] {conv_id} {msg_count}\n")

    if conv and msg_count > 12:  # COMPRESSION_THRESHOLD
        try:
            logger.info(f"[COMPRESSION_TRIGGER] Starting compression for {conv_id} with {msg_count} messages")
            from ..cognition.context_window import manage_context_window
            window = await manage_context_window(
                conversation_id=conv_id,
                messages=conv.messages,
                router=ctx.router,
                memory_store=ctx.memory,
                user_id=user_id,
            )
            # Update conversation with compressed messages
            if window.summary:
                conv.messages = window.messages
                conv.summary = window.summary  # Store summary for next interaction
                # Persist to database if using SQLite store
                if hasattr(ctx.conversations, '_persist'):
                    ctx.conversations._persist(conv)
                logger.info(f"[COMPRESSION_APPLIED] Conversation {conv_id}: {len(window.messages)} messages kept, summary length: {len(window.summary)}")
            else:
                logger.info(f"[COMPRESSION_SKIPPED] No summary generated for {conv_id}")
        except Exception as e:
            logger.error(f"[COMPRESSION_ERROR] Failed for {conv_id}: {e}", exc_info=True)

    # Memory write with LLM importance scoring (async, non-blocking)
    try:
        _score_engine = next(
            (e for e in ctx.engines if not e.caps.strong_reasoning), ctx.engines[0]
        ) if ctx.engines else None
        if _score_engine and ctx.has_semantic:
            importance = await score_importance(req.message, _score_engine)
            if importance == 5:  # fallback — use heuristic instead
                importance = 6 if use_reasoner else 4
        else:
            importance = 6 if use_reasoner else 4
    except Exception:
        importance = 6 if use_reasoner else 4

    ctx.memory.add(MemoryNode(
        content=f"用户说：{req.message}",
        user_id=user_id,
        type=MemoryType.EPISODIC,
        importance=importance,
        source="voice_capsule" if req.voice_input else "chat",
    ))

    # 记录记忆写入
    log.memory_write(
        request_id=request_id,
        node_id=f"mem_{uuid.uuid4().hex[:8]}",
        node_type="episodic",
        content_preview=f"用户说：{req.message}",
        importance=importance
    )

    # -- auto-trigger reflection if importance threshold crossed ---
    ctx.runtime.session_importance[user_id] = ctx.runtime.session_importance.get(user_id, 0) + importance
    schedule_reflection(ctx.memory, user_id, ctx.router,
                        session_importance=ctx.runtime.session_importance[user_id])

    # 记录交互完成
    log.interaction_complete(
        request_id=request_id,
        user_id=user_id,
        system_response=reply,
        total_latency_ms=trace.get("latency_ms", 0),
        tokens_used=trace.get("usage", {}).get("prompt_tokens", 0) + trace.get("usage", {}).get("completion_tokens", 0),
        cost_usd=trace.get("usage", {}).get("cost_usd", 0),
        engine_used=chosen_engine,
        success=True
    )

    return {
        "reply": reply,
        "bursts": burst_split(reply),
        "conversation_id": conv_id,
        "engine": chosen_engine,
        "system": "reasoner" if use_reasoner else "talker",
        "complexity": int(complexity),
        "risk": risk_level(req.message),
        "memory_hits": len(assembled.topic_history) if assembled else 0,
        "react_steps": react_steps,
        "trace": trace,
    }


@router.post("/stream")
async def chat_stream(req: ChatRequest, user_id: str = Depends(get_current_user)):
    """SSE streaming chat — each ReAct step is pushed as an event.

    For System 1 (talker): streams the text chunk by chunk.
    For System 2 (reasoner): pushes each Thought/Action/Observation as SSE.
    """
    async def _event_stream():
        # Input guardrails
        try:
            check_input(req.message)
        except GuardrailTripwire as t:
            yield f"data: {_json.dumps({'type': 'error', 'content': str(t.detail)})}\n\n"
            return

        # Memory retrieval
        recent_topics = _get_recent_topics(req.conversation_id)
        assembled = await build_context(req.message, user_id, ctx.memory, ctx.router, recent_topics=recent_topics)
        context_block = assembled.to_prompt_section() if assembled else ""

        # Empathy: UU analysis → IRG guidance
        empathy_snapshot, empathy_guidance = await run_empathy_pipeline(
            req.message, ctx.router,
        )

        # Dispatch
        belief = BeliefState(user_id=user_id)
        use_reasoner = needs_reasoner(req.role_hint or "chat", req.message, belief)

        system_prompt = build_prompt_with_prefs(user_id, ctx.pref_store)
        if empathy_guidance:
            system_prompt += f"\n\n[当前互动]\n{empathy_guidance}"
        if context_block:
            system_prompt += f"\n\n{context_block}"

        conv_id = req.conversation_id
        if not conv_id or not ctx.conversations.get(conv_id):
            conv = ctx.conversations.create(user_id)
            conv_id = conv.id

        if use_reasoner:
            # System 2: ReAct loop → stream each step
            react = ReActLoop(router=ctx.router, tools=ctx.tools, memory_store=ctx.memory, skills=ctx.skills,
                              max_steps=7, timeout_s=120.0)
            react_result = await react.run(
                system_prompt=system_prompt,
                user_message=req.message,
                user_id=user_id,
            )
            for s in react_result.steps:
                yield f"data: {_json.dumps({'type': s.type, 'content': s.content, 'tool_name': s.tool_name, 'tool_input': s.tool_input, 'tool_output': s.tool_output, 'latency_ms': s.latency_ms})}\n\n"
            reply = react_result.answer
            engine = "react-loop"
            system_label = "reasoner"
            trace_obj = None
        else:
            # System 1: 真正的流式输出（逐 token）
            messages = [
                EngineMessage(role="system", content=system_prompt),
                EngineMessage(role="user", content=req.message),
            ]

            # 使用路由器的流式方法
            reply = ""
            engine = None
            trace_obj = None

            # 逐 token 流式发送
            async for item in ctx.router.route_stream(CognitiveRequest(
                messages=messages,
                complexity=Complexity.L2_DAILY,
                prefer_chinese=True,
                temperature=0.7,
            )):
                # 检查是否是 trace（最后的元数据）
                if isinstance(item, tuple) and item[0] == "__trace__":
                    trace_obj = item[1]
                    engine = trace_obj.chosen or "none"
                elif isinstance(item, str):
                    # 正常的文本块
                    reply += item
                    yield f"data: {_json.dumps({'type': 'text', 'content': item})}\n\n"

            system_label = "talker"

        # Done event — include bursts for multi-bubble rendering
        done_payload = {
            "type": "done",
            "conversation_id": conv_id,
            "engine": engine,
            "system": system_label,
            "reply": reply,
            "bursts": burst_split(reply),
        }
        yield f"data: {_json.dumps(done_payload)}\n\n"

        # Persist conversation
        ctx.conversations.add_message(conv_id, "user", req.message)
        ctx.conversations.add_message(conv_id, "assistant", reply,
                         engine=engine, system=system_label)

        # Record usage stats
        if use_reasoner:
            _record_stats("react-loop", react_result.total_latency_ms, 0, 0, 0,
                          event=f"ReAct · {req.message[:40]}")
        else:
            # 使用流式路由返回的 trace
            _lat = trace_obj.latency_ms if trace_obj else 0
            _usage = trace_obj.usage if trace_obj else {}
            _record_stats(engine or "none", _lat,
                          _usage.get("prompt_tokens", 0), _usage.get("completion_tokens", 0),
                          _usage.get("cost_usd", 0),
                          event=f"{engine} · {req.message[:40]}")

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
