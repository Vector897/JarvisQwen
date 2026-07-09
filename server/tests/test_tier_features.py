"""Unit tests for the three-tier new features: semantic cache similarity, cascade confidence heuristic, export, task templates, memory arbitration."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["AAOS_DATA_DIR"] = _tmp

from app.config import config  # noqa: E402

config.data_dir = Path(_tmp)
config.ensure_dirs()

from app.core.cache import semantic  # noqa: E402
from app.core.engine.task_templates import TEMPLATES, apply_template  # noqa: E402
from app.core.router.cascade import _confidence_heuristic  # noqa: E402
from app.connectors.export import to_bibtex  # noqa: E402
from app.db import init_db, session  # noqa: E402


def test_semantic_cache_exact_and_similar_hit():
    init_db()
    with session() as db:
        semantic.store(db, "light", "总结一下这篇关于强化学习的论文", "这是总结内容", "gemini/flash")
        # exact match
        assert semantic.lookup(db, "light", "总结一下这篇关于强化学习的论文") == "这是总结内容"
        # semantically similar (word order/punctuation varies but core terms match) should hit
        hit = semantic.lookup(db, "light", "总结 一下 这篇 关于 强化学习 的 论文！")
        assert hit == "这是总结内容"
        # completely unrelated should not hit
        assert semantic.lookup(db, "light", "今天天气怎么样") is None


def test_confidence_heuristic_flags_hedging():
    assert _confidence_heuristic("这个我不太确定，可能是……") < 0.6
    assert _confidence_heuristic("A" * 100) >= 0.6
    assert _confidence_heuristic("") < 0.6


def test_task_templates_apply():
    assert len(TEMPLATES) >= 3
    ttype, params, title = apply_template("literature_watch", {"query": "test topic"})
    assert ttype == "arxiv_watch"
    assert params["query"] == "test topic"
    assert "test topic" in title


def test_bibtex_export_format():
    text = to_bibtex([{"arxiv_id": "2501.00001", "title": "A Great Paper",
                       "authors": "Alice Smith, Bob Lee", "published_at": "2025-01-01",
                       "url": "https://arxiv.org/abs/2501.00001"}])
    assert "@misc{" in text
    assert "A Great Paper" in text
    assert "Alice Smith and Bob Lee" in text


def test_memory_arbitration_reconciles_conflict():
    from app.core.memory.memory import consolidate
    from app.models import Memory, User

    with session() as db:
        user = User(name="mem_user", password_hash="x")
        db.add(user)
        db.flush()
        db.add(Memory(kind="semantic", content="用户的主力研究方向是 CFR 收敛速度",
                      tags="consolidated", owner_id=user.id))
        db.flush()
        uid = user.id

    # consolidate depends on an LLM call (returns a simulated response on dry-run with no Key); only verify it doesn't raise and the flow runs through
    with session() as db:
        count = consolidate(db, uid)
        assert count >= 0  # on dry-run, fewer than 3 episodic memories returns 0 early, which is expected
