"""SQLite-backed MemoryStore — persists memories across restarts.

Implements the same interface as MemoryStore (store.py) so main.py only
needs a one-line swap. Composite scoring remains pure-Python (min-max
normalization across the candidate set requires Python-side computation).

Embeddings are stored as JSON arrays (128 floats ~ 1KB per node); the
retrieval pipeline runs in-memory scoring, which is fast for personal scale
(~10K nodes). For production, swap to pgvector or Milvus.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .embedding import cosine, embed
from .schema import MemoryNode, MemoryType
from .store import MemoryStore, ScoredMemory, _minmax, _recency


def _ensure_utc(dt: datetime) -> datetime:
    """Attach UTC timezone to naive datetimes read from SQLite."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class SQLiteMemoryStore(MemoryStore):
    """SQLite-persisted memory store with the same retrieval algorithm."""

    def __init__(self, db_path: str = "sunday.db",
                 alpha: float = 1.0, beta: float = 1.0, gamma: float = 1.0):
        super().__init__(alpha, beta, gamma)
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    # -- schema ---------------------------------------------------------------

    def _migrate(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_nodes (
                id          TEXT PRIMARY KEY,
                user_id     TEXT    NOT NULL,
                type        TEXT    NOT NULL DEFAULT 'episodic',
                content     TEXT    NOT NULL,
                importance  INTEGER NOT NULL DEFAULT 5,
                embedding   TEXT,              -- JSON array of floats
                created_at  TEXT    NOT NULL,  -- ISO 8601
                last_access TEXT    NOT NULL,  -- ISO 8601
                access_count INTEGER NOT NULL DEFAULT 0,
                tags        TEXT    NOT NULL DEFAULT '[]',  -- JSON array
                evidence_ids TEXT   NOT NULL DEFAULT '[]',  -- JSON array
                source      TEXT    NOT NULL DEFAULT 'chat',
                frozen      INTEGER NOT NULL DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_user
                ON memory_nodes(user_id)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type
                ON memory_nodes(type)
        """)
        self._conn.commit()

    # -- node <-> row ---------------------------------------------------------

    @staticmethod
    def _row_to_node(row: tuple) -> MemoryNode:
        """Convert a SELECT * row to a MemoryNode."""
        (id_, user_id, type_, content, importance, embedding_json,
         created_at, last_access, access_count,
         tags_json, evidence_json, source, frozen) = row
        embedding = json.loads(embedding_json) if embedding_json else None
        tags = json.loads(tags_json) if tags_json else []
        evidence = json.loads(evidence_json) if evidence_json else []
        return MemoryNode(
            id=id_,
            user_id=user_id,
            type=MemoryType(type_),
            content=content,
            importance=importance,
            embedding=embedding,
            created_at=_ensure_utc(datetime.fromisoformat(created_at)),
            last_access=_ensure_utc(datetime.fromisoformat(last_access)),
            access_count=access_count,
            tags=tags,
            evidence_ids=evidence,
            source=source,
            frozen=bool(frozen),
        )

    @staticmethod
    def _node_to_params(node: MemoryNode) -> tuple:
        return (
            node.id, node.user_id, node.type.value, node.content,
            node.importance,
            json.dumps(node.embedding) if node.embedding else None,
            node.created_at.isoformat(), node.last_access.isoformat(),
            node.access_count,
            json.dumps(node.tags),
            json.dumps(node.evidence_ids),
            node.source,
            int(node.frozen),
        )

    # -- writes ---------------------------------------------------------------
    # (override the in-memory dict ops with SQLite ops)

    def add(self, node: MemoryNode) -> MemoryNode:
        if node.embedding is None:
            node.embedding = embed(node.content)
        params = self._node_to_params(node)
        self._conn.execute(
            """INSERT OR REPLACE INTO memory_nodes
               (id, user_id, type, content, importance, embedding,
                created_at, last_access, access_count,
                tags, evidence_ids, source, frozen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            params,
        )
        self._conn.commit()
        # Keep in-memory cache as well for fast scoring (retrieve still
        # pulls from SQL for freshness, but this lets tests pass unchanged)
        self._nodes[node.id] = node
        return node

    def get(self, mem_id: str) -> MemoryNode | None:
        # Check in-memory first
        if mem_id in self._nodes:
            return self._nodes[mem_id]
        row = self._conn.execute(
            "SELECT * FROM memory_nodes WHERE id = ?", (mem_id,)
        ).fetchone()
        if row is None:
            return None
        node = self._row_to_node(row)
        self._nodes[node.id] = node  # cache
        return node

    def delete(self, mem_id: str) -> bool:
        self._nodes.pop(mem_id, None)
        cur = self._conn.execute("DELETE FROM memory_nodes WHERE id = ?", (mem_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def all(self, user_id: str | None = None) -> list[MemoryNode]:
        if user_id is not None:
            rows = self._conn.execute(
                "SELECT * FROM memory_nodes WHERE user_id = ? ORDER BY last_access DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memory_nodes ORDER BY last_access DESC"
            ).fetchall()
        nodes = [self._row_to_node(r) for r in rows]
        # Update cache
        for n in nodes:
            self._nodes[n.id] = n
        return nodes

    # -- retrieval ------------------------------------------------------------
    # (override to pull candidates from SQL, then reuse scoring logic)

    def retrieve(
        self,
        query: str,
        user_id: str,
        k: int = 12,
        now: datetime | None = None,
        types: list[MemoryType] | None = None,
    ) -> list[ScoredMemory]:
        now = now or datetime.now(timezone.utc)

        # Pull candidates from SQL
        if types:
            type_vals = ",".join(f"'{t.value}'" for t in types)
            rows = self._conn.execute(
                f"SELECT * FROM memory_nodes WHERE user_id = ? AND type IN ({type_vals})",
                (user_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memory_nodes WHERE user_id = ?", (user_id,)
            ).fetchall()

        candidates = [self._row_to_node(r) for r in rows]
        if not candidates:
            return []

        # Embed query & score (same pure-logic as in-memory store)
        q_emb = embed(query)
        rec = [_recency(n, now) for n in candidates]
        imp = [n.importance / 10.0 for n in candidates]
        rel = [cosine(q_emb, n.embedding or []) for n in candidates]

        rec_n, imp_n, rel_n = _minmax(rec), _minmax(imp), _minmax(rel)

        scored = [
            ScoredMemory(
                node=n,
                score=self.alpha * rec_n[i] + self.beta * imp_n[i] + self.gamma * rel_n[i],
                recency=rec_n[i], importance=imp_n[i], relevance=rel_n[i],
            )
            for i, n in enumerate(candidates)
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        top = scored[:k]

        # Touch retrieved memories (reinforcement) — persist to SQL
        for s in top:
            s.node.last_access = now
            s.node.access_count += 1
            self._conn.execute(
                "UPDATE memory_nodes SET last_access = ?, access_count = ? WHERE id = ?",
                (now.isoformat(), s.node.access_count, s.node.id),
            )
            self._nodes[s.node.id] = s.node
        self._conn.commit()
        return top

    # -- re-embedding (embedder upgrade migration) ----------------------------

    def reembed_stale(self) -> int:
        """Re-embed nodes whose stored vector dim != the current embedder dim,
        persisting each new vector back to SQLite. See MemoryStore.reembed_stale
        for why this is needed after an embedder upgrade. Returns the count.
        """
        from .embedding import embedding_dim as _edim
        target = _edim()
        rows = self._conn.execute(
            "SELECT id, content, embedding FROM memory_nodes"
        ).fetchall()
        count = 0
        for mem_id, content, emb_json in rows:
            emb = json.loads(emb_json) if emb_json else None
            if emb and len(emb) == target:
                continue
            new_vec = embed(content)
            self._conn.execute(
                "UPDATE memory_nodes SET embedding = ? WHERE id = ?",
                (json.dumps(new_vec), mem_id),
            )
            self._nodes.pop(mem_id, None)  # invalidate cache
            count += 1
        if count:
            self._conn.commit()
        return count

    # -- consolidation --------------------------------------------------------

    def archive_expired(self, threshold: float = 0.4,
                        now: datetime | None = None) -> int:
        """Identical logic to in-memory store, but persists the deletion."""
        now = now or datetime.now(timezone.utc)
        to_drop: list[str] = []
        # Load all nodes first (cheap at personal scale)
        all_rows = self._conn.execute("SELECT * FROM memory_nodes").fetchall()
        for row in all_rows:
            node = self._row_to_node(row)
            if not node.frozen and node.importance < 10 \
               and node.effective_importance(now) < threshold:
                to_drop.append(node.id)
        for mid in to_drop:
            self._nodes.pop(mid, None)
            self._conn.execute("DELETE FROM memory_nodes WHERE id = ?", (mid,))
        if to_drop:
            self._conn.commit()
        return len(to_drop)

    # -- housekeeping ---------------------------------------------------------

    def close(self) -> None:
        self._conn.close()

    def __del__(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
