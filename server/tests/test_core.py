"""核心路径单测：Key 归一化、脱敏还原、断路器、退避、预算、引擎检查点续跑。"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# 测试用独立数据目录（必须在导入 app 模块前设置）
_tmp = tempfile.mkdtemp()
os.environ["AAOS_DATA_DIR"] = _tmp

from app.config import config  # noqa: E402

config.data_dir = Path(_tmp)
config.ensure_dirs()

from app.core.router import providers, resilience  # noqa: E402
from app.core.security.redact import redact  # noqa: E402


# ---------- Key 归一化与识别 ----------
def test_normalize_key_strips_noise():
    assert providers.normalize_key("  'sk-ant-abc123'  \n") == "sk-ant-abc123"
    assert providers.normalize_key("Bearer sk-ant-xyz") == "sk-ant-xyz"
    assert providers.normalize_key("OPENAI_API_KEY=sk-proj-foo") == "sk-proj-foo"
    assert providers.normalize_key("ｓｋ－ant－full") == "sk-ant-full"  # 全角转半角


def test_detect_provider():
    assert providers.detect_provider("sk-ant-api03-xxxx") == "anthropic"
    assert providers.detect_provider("AIzaSyABCDEF") == "google"
    assert providers.detect_provider("sk-or-v1-abc") == "openrouter"
    assert providers.detect_provider("anything", base_url="https://my.host/v1") == "custom"


def test_encrypt_roundtrip():
    enc = providers.encrypt_key("sk-secret-123")
    assert providers.decrypt_key(enc) == "sk-secret-123"
    assert "sk-secret" not in enc


# ---------- 脱敏与还原 ----------
def test_redact_and_restore():
    text = "联系 alice@example.com，密钥 sk-abcdefghijklmnop1234 别泄露"
    r = redact(text, "medium")
    assert "alice@example.com" not in r.text
    assert "sk-abcdefghijklmnop1234" not in r.text
    restored = r.restore(r.text)
    assert "alice@example.com" in restored


def test_redact_high_blocks():
    r = redact("我的 AWS 密钥是 AKIAIOSFODNN7EXAMPLE", "high")
    assert r.blocked


# ---------- 断路器与退避 ----------
def test_circuit_breaker_opens_and_recovers():
    br = resilience.CircuitBreaker(window=4, threshold=0.5, cooldown=0.05)
    for _ in range(4):
        br.report(False)
    assert not br.allow()  # 熔断
    import time

    time.sleep(0.06)
    assert br.allow()  # half-open 放探测
    br.report(True)
    assert br.state == "closed"


def test_fallback_chain():
    calls = []

    def fn(model: str) -> str:
        calls.append(model)
        if model == "bad":
            raise RuntimeError("boom")
        return "ok"

    model, result = resilience.call_with_fallbacks(["bad", "good"], fn, retries_per_model=1)
    assert model == "good" and result == "ok"
    assert calls.count("bad") == 2  # 1 次 + 1 重试


# ---------- 引擎：检查点续跑 ----------
def test_engine_checkpoint_resume():
    from app.core.engine.engine import StepDef, latest_checkpoint, register, run_task
    from app.db import init_db, session
    from app.models import Task, User

    init_db()
    executed = []

    def s1(ctx, state):
        executed.append("s1")
        state["a"] = 1
        return state

    def s2(ctx, state):
        executed.append("s2")
        if state.get("_fail_once") is None and not state.get("a_retried"):
            state["a_retried"] = True
            raise RuntimeError("模拟崩溃")
        return state

    register("_test", [StepDef("s1", s1), StepDef("s2", s2)])

    with session() as db:
        user = User(name="t_user", password_hash="x")
        db.add(user)
        db.flush()
        task = Task(type="_test", owner_id=user.id, params_json="{}")
        db.add(task)
        db.flush()
        task_id = task.id

    run_task(task_id)  # 引擎自管会话，只需 task_id
    with session() as db:
        assert db.get(Task, task_id).status == "FAILED"
        cp = latest_checkpoint(db, task_id)
        assert cp is not None and cp.step_name == "s1"  # s1 的成果被保住
        db.get(Task, task_id).status = "QUEUED"

    run_task(task_id)
    with session() as db:
        assert db.get(Task, task_id).status == "DONE"
    assert executed == ["s1", "s2", "s2"]  # 重跑没有重复执行 s1


# ---------- 会话纪律：步骤网络等待期间不得阻塞其他写者 ----------
def test_writes_not_blocked_while_step_waits_on_network():
    """本项目曾因 worker 跨网络调用持有 SQLite 写锁而全站 POST 瘫痪。
    此测试守卫会话纪律：步骤在"网络等待"（会话外耗时操作）期间，
    其他线程的写操作必须立即完成，而不是等到任务结束。"""
    import threading
    import time as _t

    from app.core.engine.engine import StepDef, register, run_task
    from app.db import init_db, session
    from app.models import Task, User

    init_db()

    def slow_network(ctx, state):
        _t.sleep(2.0)  # 模拟 LLM/PDF 下载等网络等待（正确写法：不持有会话）
        return state

    register("_locktest", [StepDef("net", slow_network)])
    with session() as db:
        user = User(name="lock_user", password_hash="x")
        db.add(user)
        db.flush()
        task = Task(type="_locktest", owner_id=user.id, params_json="{}")
        db.add(task)
        db.flush()
        task_id, owner_id = task.id, user.id

    worker = threading.Thread(target=run_task, args=(task_id,))
    worker.start()
    _t.sleep(0.5)  # 等 worker 进入 slow_network 的等待段
    t0 = _t.time()
    with session() as db:  # 模拟 API 线程的 POST 写入
        db.add(Task(type="_locktest", owner_id=owner_id, params_json="{}", status="CANCELLED"))
    blocked_for = _t.time() - t0
    worker.join()
    assert blocked_for < 1.0, f"并发写被阻塞 {blocked_for:.2f}s——步骤执行期间不应持有写锁"


# ---------- 预算熔断 ----------
def test_budget_cutoff():
    from app.core.budget.guard import BudgetExceeded, check
    from app.core.settings_store import set_setting
    from app.db import init_db, session
    from app.models import AuditLog

    init_db()
    with session() as db:
        set_setting(db, "daily_budget_usd", 0.01)
        db.add(AuditLog(cost_usd=0.02))
        db.flush()
        with pytest.raises(BudgetExceeded):
            check(db)
