"""语义缓存 V2：词袋余弦相似度（纯 Python，无需外部向量库/embedding API 调用）。

设计取舍：真正的 embedding 向量缓存需要额外的 embedding API 调用（有成本）或
向量数据库（Qdrant，见架构文档 V2 升级路径）。这里用词频向量+余弦相似度实现
「语义相近也能命中」的核心效果，零额外成本、零新增基础设施，适合个人/小团队规模
（候选池数百条时性能足够；超大规模需迁移到 Qdrant，接口保持不变）。
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

_WORD_RE = re.compile(r"[a-zA-Z]+|[一-鿿]")  # 英文单词 或 单个中文字
SIMILARITY_THRESHOLD = 0.93  # 相似度阈值：高于此值视为「同一问题」


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

    # ① 精确匹配（最快，命中率高的常规路径）
    exact = db.execute(select(LlmCache).where(LlmCache.id == _exact_key(tier, prompt))).scalar_one_or_none()
    if exact is not None and exact.expires_at >= now:
        exact.hit_count += 1
        return exact.response

    # ② 语义相似匹配：同层未过期缓存中找余弦相似度最高者
    query_vec = _tokenize(prompt)
    if not query_vec:
        return None
    candidates = db.execute(
        select(LlmCache).where(LlmCache.model.like(f"{tier}::%"), LlmCache.expires_at >= now)
    ).scalars().all()
    best_row, best_score = None, 0.0
    for row in candidates:
        # model 字段编码为 "tier::原模型::原prompt摘要"；这里用存储的 prompt_bow 字段近似，
        # 简化实现：直接对 response 前置存储的原始 prompt 做比较（见 store() 中 id 的可逆哈希不可行，
        # 因此改为把原始 prompt 存一份轻量索引，见下方 _PROMPT_INDEX）。
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


# 进程内轻量索引：id -> 词频向量（重启后清空，退化为仅精确匹配，不影响正确性）
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
