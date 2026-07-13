"""Runtime — the skeletal interface of a running Sunday instance.

Every subsystem is mounted here. Each field = a single point of truth for
"what Sunday consists of at runtime."

The LINKAGE section (§2) documents the data flow between subsystems —
which module calls which, in what order. This is the "联动性" contract:
when you add or change a module, update its linkage entry.

Design rules:
  1. Every subsystem is reachable through runtime.<name> — never hidden.
  2. Linkages are NAMED objects, not ad-hoc function calls.
  3. Adding a new subsystem = 1 field here + 1 linkage entry.
  4. No subsystem imports another directly through runtime — they receive
     what they need as constructor/function args. Runtime is the HOLDER,
     not the caller.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict as _dd
from dataclasses import dataclass, field
from datetime import datetime as _dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cognition.react_loop import ReActLoop
    from .cognition.tools import ToolRegistry, SkillRegistry
    from .conversation.store import ConversationStore
    from .engines.base import EngineProvider
    from .engines.router import CognitiveRouter
    from .memory.store import MemoryStore

# ---------------------------------------------------------------------------
# 1. Runtime — the container
# ---------------------------------------------------------------------------

@dataclass
class Runtime:
    """Holds every live subsystem. Created once at startup."""

    engines: list[EngineProvider]
    router: CognitiveRouter
    memory: MemoryStore
    conversations: ConversationStore
    tools: ToolRegistry
    skills: SkillRegistry

    # -- identity ----------------------------------------------------------
    _user_cache: dict[str, str] = field(default_factory=lambda: {})

    def resolve_user(self, api_key: str | None) -> str:
        """API Key → stable user_id. Cached. Same key = same identity everywhere."""
        raw = (api_key or "anonymous")
        cached = self._user_cache.get(raw)
        if cached:
            return cached
        uid = "user_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        self._user_cache[raw] = uid
        if len(self._user_cache) > 1000:
            self._user_cache.clear()
        return uid

    # -- usage stats (cross-cutting) ---------------------------------------
    messages_today: int = 0
    calls_today: int = 0
    tokens_today: int = 0
    cost_today: float = 0.0
    total_latency_ms: float = 0.0
    call_count: int = 0
    engine_calls: dict = field(default_factory=lambda: _dd(int))
    recent_events: list = field(default_factory=list)
    session_importance: dict = field(default_factory=dict)

    def record_call(
        self, engine_id: str | None, latency_ms: float,
        prompt_tokens: int, completion_tokens: int, cost_usd: float,
        event: str = "",
    ) -> None:
        self.messages_today += 1
        self.calls_today += 1
        self.tokens_today += prompt_tokens + completion_tokens
        self.cost_today += cost_usd
        self.total_latency_ms += latency_ms
        self.call_count += 1
        if engine_id:
            self.engine_calls[engine_id] += 1
        if event:
            self.recent_events.insert(0, {"time": _dt.now().isoformat(), "event": event})
            self.recent_events = self.recent_events[:20]
            #           ^ keep bounded

    @property
    def avg_latency(self) -> float:
        if self.call_count == 0:
            return 0.0
        return round(self.total_latency_ms / self.call_count, 1)

    semantic_embedder_available: bool = False  # set by main.py after upgrade


# ---------------------------------------------------------------------------
# 2. LINKAGE — documented data flow between subsystems
# ---------------------------------------------------------------------------
#
# This is the "联动性" contract. Every linkage is a named pattern
# describing WHO calls WHOM, through WHAT data, in WHAT order.
#
# When you ADD a new module: add its linkage entry here.
# When you CHANGE a module: update its linkage entry.
# When you REMOVE a module: delete its linkage entry + its Runtime field.
#
# LINKAGE: chat_pipeline
#   Actor: main.py chat endpoint
#   Flow:
#     1. check_input(message)              [guardrails/pipeline]
#     2. empathy = analyze_user(message)   [persona/empathy → UU]
#     3. ctx = build_context(message)      [cognition/context_builder]
#         → uses runtime.memory + runtime.router
#     4. needs_reasoner?(message, belief)  [cognition/dispatch]
#     5a. (System1) router.route(msg)      [engines/router]
#     5b. (System2) ReActLoop.run(msg)     [cognition/react_loop]
#         → uses runtime.tools + runtime.memory + runtime.router
#     6. belief_state.update(result)       [cognition/belief]
#     7. memory.add(episodic_node)         [memory/store]
#     8. schedule_reflection(memory)       [memory/reflection → background]
#
# LINKAGE: reflection_l1_to_l2
#   Actor: memory/reflection (background task)
#   Flow:
#     1. _should_reflect(store, user_id)          [importance threshold]
#     2. _generate_questions(store, router)       [LLM → 3 questions]
#     3. for each: store.retrieve(q) → _synthesize_insight(...)  [LLM → insight]
#     4. store.add(REFLECTION node)                [write back]
#     5. (recursive) if cumulative importance > θ → repeat
#   Data: MemoryStore ↔ CognitiveRouter (no other coupling)
#
# LINKAGE: experience_l2_to_l3
#   Actor: memory/experience (batch job)
#   Flow:
#     1. _merge_similar(store)                    [cosine dedup]
#     2. _archive_expired(store)                  [importance decay]
#     3. _extract_semantic(store, router)         [LLM → facts]
#     4. detect_patterns(store, router)           [LLM → patterns]
#     5. encapsulate_procedures(store, router)    [LLM → primitives]
#   Data: MemoryStore ↔ CognitiveRouter (no other coupling)
#
# LINKAGE: persona_loading
#   Actor: persona/__init__
#   Dependent on: persona.yaml (filesystem, Git-versioned)
#   Consumed by: main.py → build_system_prompt()
#   Data: persona.yaml → dict → system_prompt_string
#   No runtime dependency (pure filesystem read)
#
# LINKAGE: empathy_pipeline
#   Actor: persona/empathy
#   Flow:
#     1. analyze_user(message, router)            [UU → emotion + dialogue_act]
#     2. build_empathy_guidance(snapshot)          [IRG → prompt injection]
#     3. belief.emotional_state.update(snapshot)   [smooth EMA transition]
#   Data: CognitiveRouter (for classification LLM call)
#
# LINKAGE: memory_retrieval
#   Actor: memory/store (called by context_builder, chat pipeline, etc.)
#   Flow:
#     1. embed(query)                              [embedding module]
#     2. score = α·recency + β·importance + γ·relevance   [composite]
#     3. min-max normalize across candidates       [per-component]
#     4. sort ↓, return top-k ScoredMemory
#   Data: MemoryStore is self-contained. Only dependency: embed() function.
#
# ===== LINKAGE GRAPH (who calls whom) =====
#
#   main.py
#    ├── runtime.resolve_user()
#    ├── guardrails.check_input(message)
#    ├── persona/empathy.analyze_user(message, router)    → UU snapshot
#    ├── persona/empathy.build_empathy_guidance(snapshot) → IRG string
#    ├── persona/build_system_prompt()                    → persona string
#    ├── cognition/context_builder.build_context(m, uid, store, router)
#    │     └── memory/store.retrieve() × N               → ScoredMemories
#    ├── cognition/dispatch.needs_reasoner()
#    ├── cognition/react_loop.ReActLoop.run()
#    │     ├── engines/router.route() × N                → LLM response
#    │     └── tools.execute() × N                       → tool output
#    ├── memory/store.add(episodic_node)
#    └── memory/reflection.schedule_reflection()          → background task
#
#   (background)
#   memory/reflection.run_reflection()
#    ├── engines/router.route()                          → LLM (questions)
#    └── engines/router.route() × 3                      → LLM (insights)
#
#   (batch)
#   memory/experience.run_experience_layer()
#    ├── memory/store (merge + archive)
#    ├── engines/router.route()                          → LLM (extract)
#    ├── engines/router.route()                          → LLM (patterns)
#    └── engines/router.route()                          → LLM (primitives)
# ===== END LINKAGE =====
