"""Pluggable embedder. Default is a deterministic, offline, dependency-free
hashing embedder so retrieval scoring is testable without any network/model.
Swap in a real embedding model in production via set_embedder()."""
from __future__ import annotations

import hashlib
import math
from typing import Callable

_DIM = 128


def _hash_embed(text: str, dim: int = _DIM) -> list[float]:
    """Bag-of-tokens hashing → L2-normalized vector. Deterministic."""
    vec = [0.0] * dim
    tokens = text.lower().split()
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


_embedder: Callable[[str], list[float]] = _hash_embed


def set_embedder(fn: Callable[[str], list[float]]) -> None:
    global _embedder
    _embedder = fn


def embed(text: str) -> list[float]:
    return _embedder(text)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
