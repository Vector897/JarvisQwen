"""AAOS backend entry point: wire up routes, start the scheduler, crash recovery.

Run: uvicorn app.main:app --host 0.0.0.0 --port 8000
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
from .core.engine import graphs  # noqa: F401  importing registers the task graphs
from .core.router import providers
from .core.scheduler import runner
from .access import AccessGateMiddleware
from .db import init_db
from .ratelimit import RateLimitMiddleware

_scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    init_db()
    ensure_admin_user()
    providers.import_env_keys()  # auto-import into the DB when DASHSCOPE_API_KEY is present in .env
    runner.start(_scheduler)  # worker thread + scheduled jobs + recovery of crashed tasks
    _scheduler.start()
    print(f"[JarvisQwen] v{__version__} control plane up at http://{config.host}:{config.port}")
    yield
    runner.stop()
    _scheduler.shutdown(wait=False)


app = FastAPI(title="AAOS", version=__version__, lifespan=lifespan)

if config.access_code:  # optional access-code gate (guards public demos against strangers burning quota)
    app.add_middleware(AccessGateMiddleware, code=config.access_code)

if config.ratelimit_enabled:  # inbound rate limiting (outermost layer, ahead of route handling)
    app.add_middleware(RateLimitMiddleware, rpm=config.ratelimit_rpm)

if config.web_origin:  # CORS fallback for mode B when not going through Vercel rewrites
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
