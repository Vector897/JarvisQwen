"""AAOS 后端入口：装配路由、启动调度器、崩溃恢复。

运行：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api import auth_api, events, keys, misc, tasks, users
from .auth import ensure_admin_user
from .config import config
from .core.engine import graphs  # noqa: F401  导入即注册任务图
from .core.scheduler import runner
from .db import init_db

_scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    init_db()
    ensure_admin_user()
    runner.start(_scheduler)  # 工作线程 + 定时作业 + 崩溃任务恢复
    _scheduler.start()
    print(f"[AAOS] v{__version__} 控制平面已启动  http://{config.host}:{config.port}")
    yield
    runner.stop()
    _scheduler.shutdown(wait=False)


app = FastAPI(title="AAOS", version=__version__, lifespan=lifespan)

if config.web_origin:  # 模式 B 且未走 Vercel rewrites 时的 CORS 兜底
    app.add_middleware(
        CORSMiddleware, allow_origins=[config.web_origin],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

app.include_router(auth_api.router)
app.include_router(keys.router)
app.include_router(tasks.router)
app.include_router(misc.router)
app.include_router(events.router)
app.include_router(users.router)


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": __version__}
