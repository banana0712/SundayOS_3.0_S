"""ChromaDB vector store — persistent semantic search for memory.

Uses Chroma in embedded mode (PersistentClient); zero external services.
Each MemoryNode is indexed when written; semantic search returns ranked
node IDs that the SQLite store can retrieve.

In Phase 1 this is an optional add-on (hash embedder still works).
Auto-upgraded when a semantic embedder is available (see embedding.py).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chromadb.api import Collection

logger = logging.getLogger(__name__)

_COLLECTION = "sunday_memories"


class VectorStore:
    """Semantic search over memory embeddings using ChromaDB."""

    def __init__(self, persist_dir: str = "./chroma_db"):
        self._persist_dir = persist_dir
        self._client = None
        self._collection: Collection | None = None

    # -- lazy init (avoids import on startup when chromadb is missing) -------

    def _ensure(self) -> Collection:
        if self._collection is not None:
            return self._collection
        try:
            import chromadb  # noqa: F811
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except ImportError:
            raise RuntimeError(
                "chromadb is not installed. Run: pip install chromadb"
            )

    @property
    def ready(self) -> bool:
        try:
            self._ensure()
            return True
        except (ImportError, RuntimeError):
            return False

    # -- CRUD -----------------------------------------------------------------

    def add(self, node_id: str, content: str, embedding: list[float],
            metadata: dict | None = None) -> None:
        """Index a memory node. Call after SQLite write."""
        try:
            coll = self._ensure()
            meta = (metadata or {})
            coll.upsert(
                ids=[node_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[{k: str(v) for k, v in meta.items()}],
            )
        except (ImportError, RuntimeError) as e:
            logger.debug("VectorStore.add skipped: %s", e)

    def delete(self, node_id: str) -> None:
        """Remove a node from the index."""
        try:
            coll = self._ensure()
            coll.delete(ids=[node_id])
        except (ImportError, RuntimeError) as e:
            logger.debug("VectorStore.delete skipped: %s", e)

    # -- search ---------------------------------------------------------------

    def search(self, query_embedding: list[float], k: int = 12,
               where: dict | None = None) -> list[str]:
        """Return node IDs ranked by semantic similarity.

        Args:
            query_embedding: the query vector (same dim as stored embeddings)
            k: top-k results
            where: optional Chroma metadata filter, e.g. {"user_id": "u1"}
        """
        try:
            coll = self._ensure()
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
            )
            ids = results.get("ids", [[]])[0] if results else []
            return list(ids)
        except (ImportError, RuntimeError) as e:
            logger.debug("VectorStore.search skipped: %s", e)
            return []

    def search_by_text(self, query: str, embed_fn, k: int = 12,
                       where: dict | None = None) -> list[str]:
        """Embed query text → semantic search. Convenience wrapper."""
        q_emb = embed_fn(query)
        return self.search(q_emb, k=k, where=where)

    def count(self) -> int:
        try:
            coll = self._ensure()
            return coll.count()
        except (ImportError, RuntimeError):
            return 0
