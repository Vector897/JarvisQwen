"""调度器：工作线程轮询队列（租约防双消费）+ 看门狗 + 订阅触发 + 夜间维护。"""
from __future__ import annotations

import json
import os
import threading
import time
import traceback

from sqlalchemy import select

from ...db import session
from ...models import Subscription, Task, User
from ..bus import bus
from ..engine.engine import run_task
from ..settings_store import get_setting

LEASE_SECONDS = 30 * 60  # 单任务租约上限（看门狗依据）
WORKERS = int(os.environ.get("AAOS_WORKERS", "3"))  # 并发工作线程数：任务多为 LLM 网络等待，多线程可并行
_stop = threading.Event()
_claim_lock = threading.Lock()  # 多 worker 同进程，用线程锁保证"查询+写租约"原子，防双消费


def _claim_next() -> str | None:
    """领取一个排队任务（写租约），返回 task_id。"""
    with _claim_lock, session() as db:
        task = db.execute(
            select(Task).where(Task.status == "QUEUED")
            .order_by(Task.priority, Task.created_at).limit(1)
        ).scalars().first()
        if task is None:
            return None
        task.status = "RUNNING"
        task.lease_until = time.time() + LEASE_SECONDS
        return task.id


def worker_loop() -> None:
    while not _stop.is_set():
        task_id = None
        try:
            task_id = _claim_next()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        if task_id is None:
            _stop.wait(2)
            continue
        try:
            with session() as db:
                task = db.execute(select(Task).where(Task.id == task_id)).scalar_one()
                run_task(db, task)
        except Exception:  # noqa: BLE001  引擎内部已兜底，这里防调度器线程死亡
            traceback.print_exc()
            with session() as db:
                task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
                if task and task.status == "RUNNING":
                    task.status = "FAILED"
                    task.error = "Scheduler error - task can be rerun from checkpoint"


def watchdog() -> None:
    """租约过期的 RUNNING 任务 → ZOMBIE 回收 → 重新排队（从检查点续跑）。"""
    with session() as db:
        rows = db.execute(
            select(Task).where(Task.status == "RUNNING", Task.lease_until < time.time())
        ).scalars().all()
        for t in rows:
            t.status = "QUEUED"  # 检查点仍在，重跑不重复付费
            t.error = "Watchdog reclaim: execution timed out (zombie); re-queued from checkpoint"
            bus.publish("task_zombie_requeued", {"task_id": t.id})


def check_subscriptions() -> None:
    """到期的订阅 → 派生 arxiv_watch 任务。"""
    with session() as db:
        now = time.time()
        subs = db.execute(select(Subscription).where(Subscription.enabled == 1)).scalars().all()
        for sub in subs:
            if now - sub.last_run_at < sub.interval_minutes * 60:
                continue
            sub.last_run_at = now
            db.add(Task(
                type="arxiv_watch", title=f"Subscription poll: {sub.query}",
                params_json=json.dumps({"query": sub.query, "max_results": 15}, ensure_ascii=False),
                owner_id=sub.owner_id, priority=7,
            ))


def nightly_consolidate() -> None:
    from ..cache.semantic import evict_expired
    from ..memory.memory import consolidate, decay_heat

    with session() as db:
        for user in db.execute(select(User)).scalars().all():
            try:
                consolidate(db, user.id)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
        decay_heat(db)
        evict_expired(db)


def daily_briefing() -> None:
    with session() as db:
        for user in db.execute(select(User).where(User.role != "viewer")).scalars().all():
            db.add(Task(type="briefing", title="Morning briefing", owner_id=user.id, priority=3,
                        params_json="{}"))


def recover_on_boot() -> None:
    """启动钩子：崩溃前 RUNNING 的任务重新排队（检查点续跑）。"""
    with session() as db:
        rows = db.execute(select(Task).where(Task.status == "RUNNING")).scalars().all()
        for t in rows:
            t.status = "QUEUED"


def start(scheduler) -> list[threading.Thread]:
    """启动工作线程池并注册 APScheduler 定时作业。scheduler: BackgroundScheduler。"""
    recover_on_boot()
    threads = []
    for i in range(WORKERS):
        thread = threading.Thread(target=worker_loop, name=f"aaos-worker-{i}", daemon=True)
        thread.start()
        threads.append(thread)

    with session() as db:
        briefing_hour = int(get_setting(db, "briefing_hour"))
        consolidate_hour = int(get_setting(db, "consolidate_hour"))
    scheduler.add_job(watchdog, "interval", seconds=60, id="watchdog")
    scheduler.add_job(check_subscriptions, "interval", minutes=5, id="subscriptions")
    from ...connectors.telegram_bot import poll_commands
    scheduler.add_job(poll_commands, "interval", seconds=20, id="telegram_remote")
    scheduler.add_job(nightly_consolidate, "cron", hour=consolidate_hour, id="consolidate")
    scheduler.add_job(daily_briefing, "cron", hour=briefing_hour, minute=30, id="briefing")
    return threads


def stop() -> None:
    _stop.set()
