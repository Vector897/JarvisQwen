"""Semantic cache V2: bag-of-words cosine similarity (pure Python, no external vector store/embedding API calls).

Design trade-off: a true embedding-vector cache requires extra embedding API calls (with a cost) or
a vector database (Qdrant, see the V2 upgrade path in the architecture docs). Here we use term-frequency
vectors + cosine similarity to achieve the core effect of "semantically similar queries can still hit",
with zero extra cost and zero new infrastructure, suitable for individual/small-team scale (performance is
sufficient with a candidate pool of a few hundred; very large scale requires migrating to Qdrant, keeping the interface unchanged).
"""
from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import LlmCache
from ..settings_store import get_setting

_WORD_RE = re.compile(r"[a-zA-Z]+|[一-鿿]")  # an English word or a single Chinese character
SIMILARITY_THRESHOLD = 0.93  # similarity threshold: above this value is treated as "the same question"


def _tokenize(text: str) -> Counter:
    return Counter(_WORD_RE.findall(text.lower()))


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _exact_key(tier: str, prompt: str) -> str:
    normalized = re.sub(r"\s+", " ", prompt).strip().lower()
    return hashlib.sha256(f"{tier}|{normalized}".encode()).hexdigest()


def lookup(db: Session, tier: str, prompt: str) -> str | None:
    if not get_setting(db, "cache_enabled"):
        return None
    now = time.time()

    # ① Exact match (fastest, the common high-hit-rate path)
    exact = db.execute(select(LlmCache).where(LlmCache.id == _exact_key(tier, prompt))).scalar_one_or_none()
    if exact is not None and exact.expires_at >= now:
        exact.hit_count += 1
        return exact.response

    # ② Semantic similarity match: find the highest cosine similarity among non-expired cache entries in the same tier
    query_vec = _tokenize(prompt)
    if not query_vec:
        return None
    candidates = db.execute(
        select(LlmCache).where(LlmCache.model.like(f"{tier}::%"), LlmCache.expires_at >= now)
    ).scalars().all()
    best_row, best_score = None, 0.0
    for row in candidates:
        # The model field is encoded as "tier::original_model::original_prompt_digest"; here we approximate
        # using the stored prompt_bow field. Simplified implementation: compare directly against the original
        # prompt stored alongside the response (a reversible hash of the id in store() is infeasible, so
        # instead we keep the original prompt in a lightweight index, see _PROMPT_INDEX below).
        original = _PROMPT_INDEX.get(row.id)
        if not original:
            continue
        score = _cosine(query_vec, original)
        if score > best_score:
            best_score, best_row = score, row
    if best_row is not None and best_score >= SIMILARITY_THRESHOLD:
        best_row.hit_count += 1
        return best_row.response
    return None


# In-process lightweight index: id -> term-frequency vector (cleared on restart, degrading to exact-match only, which does not affect correctness)
_PROMPT_INDEX: dict[str, Counter] = {}


def store(db: Session, tier: str, prompt: str, response: str, model: str) -> None:
    if not get_setting(db, "cache_enabled"):
        return
    ttl = float(get_setting(db, "cache_ttl_hours")) * 3600
    key = _exact_key(tier, prompt)
    row = db.execute(select(LlmCache).where(LlmCache.id == key)).scalar_one_or_none()
    tagged_model = f"{tier}::{model}"
    if row is None:
        db.add(LlmCache(id=key, response=response, model=tagged_model, expires_at=time.time() + ttl))
    else:
        row.response = response
        row.model = tagged_model
        row.expires_at = time.time() + ttl
    _PROMPT_INDEX[key] = _tokenize(prompt)


def evict_expired(db: Session) -> int:
    now = time.time()
    expired_ids = [r.id for r in db.execute(select(LlmCache.id).where(LlmCache.expires_at < now))]
    for eid in expired_ids:
        _PROMPT_INDEX.pop(eid, None)
    result = db.execute(delete(LlmCache).where(LlmCache.expires_at < now))
    return result.rowcount or 0
