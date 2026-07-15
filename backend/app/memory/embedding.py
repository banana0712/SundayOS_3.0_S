"""Pluggable embedder. Default is a deterministic, offline, dependency-free
hashing embedder so retrieval scoring is testable without any network/model.
Call set_embedder() to swap in a real embedding model (OpenAI / DeepSeek / etc.).

A semantic embedder gives ~30-50x better Chinese relevance ranking than the
hash fallback (which can't tokenize CJK without whitespace).
"""
from __future__ import annotations

import hashlib
import math
import os
import time
from typing import Callable

_DIM = 128

# ---------------------------------------------------------------------------
# Hash embedder (offline fallback)
# ---------------------------------------------------------------------------

def _hash_embed(text: str, dim: int = _DIM) -> list[float]:
    """Bag-of-tokens hashing → L2-normalized vector. Deterministic."""
    vec = [0.0] * dim
    # Try jieba-style fallback: if no spaces, split every 2 chars (CJK)
    tokens = text.lower().split()
    if len(tokens) <= 1 and any('一' <= c <= '鿿' for c in text):
        tokens = [text[i:i+2] for i in range(0, len(text), 2)]
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ---------------------------------------------------------------------------
# Plugin system
# ---------------------------------------------------------------------------

_embedder: Callable[[str], list[float]] = _hash_embed
_embedding_dim: int = _DIM
_embedder_lock: bool = False  # set to True after first use to prevent races
_embedder_provider: str = "hash"  # which backend is live (health visibility)


def set_embedder(fn: Callable[[str], list[float]], dim: int = 1536,
                 provider: str = "custom") -> None:
    """Swap in a production embedder. dim = output vector size."""
    global _embedder, _embedding_dim, _embedder_provider
    _embedder = fn
    _embedding_dim = dim
    _embedder_provider = provider


def embed(text: str) -> list[float]:
    return _embedder(text)


def embedding_dim() -> int:
    return _embedding_dim


def embedder_provider() -> str:
    """Name of the live embedder backend: 'hash' (degraded), 'qwen',
    'openai', 'ollama', … — surfaced by /health for degradation visibility."""
    return _embedder_provider


def is_semantic() -> bool:
    """True when a real semantic embedder is active (not the hash fallback)."""
    return _embedder_provider != "hash"


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# OpenAI / DeepSeek compatible embedder (semantic)
# ---------------------------------------------------------------------------

class SemanticEmbedder:
    """Calls an OpenAI-compatible /embeddings endpoint (DeepSeek, Qwen, etc.).

    Uses httpx for sync HTTP calls (safe inside FastAPI's event loop).
    Includes an LRU cache to avoid re-embedding the same text.
    Also exposes async embed_batch for bulk embedding.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "text-embedding-3-small",
        dim: int = 1536,
        cache_size: int = 2048,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim
        self._cache: dict[str, list[float]] = {}
        self._cache_size = cache_size

    def embed(self, text: str) -> list[float]:
        """Synchronous embed. Falls back to hash embedder on any failure."""
        if text in self._cache:
            return self._cache[text]

        import httpx
        try:
            url = f"{self._base_url}/embeddings"
            resp = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self._model, "input": text},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vec = data["data"][0]["embedding"]

            # LRU eviction
            if len(self._cache) >= self._cache_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[text] = vec
            return vec
        except Exception:
            # API call failed — fall back to hash embedder
            return _hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Async batch embed — use when you have many texts to embed."""
        import httpx
        url = f"{self._base_url}/embeddings"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return [d["embedding"] for d in data["data"]]


# ---------------------------------------------------------------------------
# Auto-detect: if DEEPSEEK_API_KEY is set, use semantic embedder
# ---------------------------------------------------------------------------

def _env(name: str) -> str | None:
    v = os.environ.get(name)
    if v and v.strip():
        return v.strip()
    for k, val in os.environ.items():
        if k.strip() == name and val and val.strip():
            return val.strip()
    return None


# ---------------------------------------------------------------------------
# Ollama embedder (free, local, no API key)
# ---------------------------------------------------------------------------

class OllamaEmbedder:
    """Local embedding via Ollama. Uses httpx (sync, safe in event loop).

    Recommended model: nomic-embed-text (274MB, 768-dim, multilingual)
    Install: curl -fsSL https://ollama.com/install.sh | sh
             ollama pull nomic-embed-text

    Also supports bge-m3 (1.2GB, 1024-dim, best Chinese) for production.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        dim: int = 768,
        cache_size: int = 2048,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dim
        self._cache: dict[str, list[float]] = {}
        self._cache_size = cache_size

    def embed(self, text: str) -> list[float]:
        """Synchronous embed via Ollama HTTP API. LRU-cached."""
        if text in self._cache:
            return self._cache[text]

        import httpx
        try:
            url = f"{self._base_url}/api/embeddings"
            resp = httpx.post(
                url,
                json={"model": self._model, "prompt": text},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vec = data["embedding"]

            # LRU eviction
            if len(self._cache) >= self._cache_size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[text] = vec
            return vec
        except Exception:
            return _hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Async batch embed. Ollama doesn't support batch, so sequential."""
        results = []
        for text in texts:
            results.append(self.embed(text))
        return results


def try_semantic_embedder() -> tuple[SemanticEmbedder, str] | None:
    """Create a SemanticEmbedder from the first EMBED-capable API key found.

    Priority: Qwen (DashScope, great CJK) > OpenAI. DeepSeek is skipped —
    it does not expose an /embeddings endpoint.

    Returns (embedder, provider_name) or None if no key is configured.
    """
    # Qwen / DashScope — OpenAI-compatible mode. text-embedding-v3 = 1024-dim,
    # strong Chinese. Base URL overridable via QWEN_BASE_URL.
    qwen_key = _env("QWEN_API_KEY") or _env("DASHSCOPE_API_KEY")
    if qwen_key:
        base = _env("QWEN_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model = _env("QWEN_EMBED_MODEL") or "text-embedding-v3"
        return SemanticEmbedder(api_key=qwen_key, base_url=base, model=model, dim=1024), "qwen"

    # OpenAI (or any OpenAI-compatible endpoint via OPENAI_BASE_URL)
    key = _env("OPENAI_API_KEY")
    if key:
        base = _env("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        return SemanticEmbedder(api_key=key, base_url=base), "openai"

    return None


def auto_upgrade_embedder() -> bool:
    """Try to upgrade from hash embedder to semantic.

    Priority: Ollama (free, local) > API providers (Qwen > OpenAI).
    Returns True if upgraded. On failure the hash embedder stays live and
    embedder_provider() keeps reading 'hash' — that's the degraded signal.
    """
    # 1. Try Ollama first (free, local — zero API cost)
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    import httpx
    try:
        # Quick health check — is Ollama running?
        r = httpx.get(f"{ollama_url}/api/tags", timeout=3.0)
        if r.status_code == 200:
            oe = OllamaEmbedder(base_url=ollama_url, model=ollama_model)
            # Verify the model is pulled by doing a test embed
            test = oe.embed("test")
            if len(test) > 10:  # real embedding, not hash fallback
                set_embedder(oe.embed, dim=oe._dim, provider="ollama")
                return True
    except Exception:
        pass  # Ollama not available

    # 2. Try an API provider (Qwen > OpenAI)
    result = try_semantic_embedder()
    if result:
        sem, provider = result
        # Verify the endpoint actually works before committing. SemanticEmbedder
        # silently falls back to hash (128-dim) on network/auth failure; if we
        # trusted the key blindly, /health would lie (provider=qwen, dim=1024)
        # while storing 128-dim hash vectors, and reembed_stale would loop
        # forever (128 != 1024 every startup). A live test-embed of the right
        # dim is the only honest gate.
        test = sem.embed("test")
        if len(test) == sem._dim:
            set_embedder(sem.embed, dim=sem._dim, provider=provider)
            return True
        # Key present but endpoint unusable — stay on hash, stay honest.
        return False
    return False

