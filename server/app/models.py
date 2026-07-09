"""All ORM models (data model layer)."""
from __future__ import annotations

import time
import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return uuid.uuid4().hex


def now() -> float:
    return time.time()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16), default="member")  # admin/member/viewer
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[float] = mapped_column(Float, default=now)


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    provider: Mapped[str] = mapped_column(String(32))  # qwen/anthropic/openai/google/deepseek/openrouter/custom
    encrypted_key: Mapped[str] = mapped_column(Text)
    base_url: Mapped[str] = mapped_column(String(256), default="")  # custom OpenAI-compatible endpoint
    label: Mapped[str] = mapped_column(String(64), default="")
    priority: Mapped[int] = mapped_column(Integer, default=0)  # rotation order across multiple keys
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/rate_limited/broken
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    type: Mapped[str] = mapped_column(String(32))  # echo/arxiv_watch/summarize/briefing/survey
    title: Mapped[str] = mapped_column(String(256), default="")
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1 is highest
    # QUEUED/RUNNING/SUSPENDED/WAITING_APPROVAL/DONE/FAILED/ZOMBIE/CANCELLED
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", index=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    budget_limit_usd: Mapped[float] = mapped_column(Float, default=1.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0)  # 0..1
    eta_ts: Mapped[float] = mapped_column(Float, default=0)  # estimated completion timestamp; 0 = unknown
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[float] = mapped_column(Float, default=now)
    finished_at: Mapped[float] = mapped_column(Float, default=0)


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    task_id: Mapped[str] = mapped_column(String(32), ForeignKey("tasks.id"), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    step_name: Mapped[str] = mapped_column(String(64))
    state_json: Mapped[str] = mapped_column(Text)  # task state snapshot; basis for resume-from-checkpoint
    created_at: Mapped[float] = mapped_column(Float, default=now)


class StepStat(Base):
    """Per-step historical duration for each task type (exponential moving average); basis for ETA calculation."""

    __tablename__ = "step_stats"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)  # f"{task_type}:{step_name}"
    duration_p50: Mapped[float] = mapped_column(Float, default=0)
    duration_p90: Mapped[float] = mapped_column(Float, default=0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(32), default="arxiv")
    query: Mapped[str] = mapped_column(String(512))  # arXiv search query or keywords
    interval_minutes: Mapped[int] = mapped_column(Integer, default=360)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    last_run_at: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Paper(Base):
    __tablename__ = "papers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    arxiv_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    doi: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(String(512))
    authors: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[str] = mapped_column(String(32), default="")
    url: Mapped[str] = mapped_column(String(256), default="")
    pdf_path: Mapped[str] = mapped_column(String(512), default="")
    dedup_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Summary(Base):
    __tablename__ = "summaries"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    paper_id: Mapped[str] = mapped_column(String(32), ForeignKey("papers.id"), index=True)
    model: Mapped[str] = mapped_column(String(64), default="")
    content_md: Mapped[str] = mapped_column(Text)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String(16), default="episodic")  # episodic/semantic
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[str] = mapped_column(String(256), default="")
    ts: Mapped[float] = mapped_column(Float, default=now)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    heat: Mapped[float] = mapped_column(Float, default=1.0)  # access frequency × recency; decays overnight
    archived: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))


class Briefing(Base):
    __tablename__ = "briefings"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    date: Mapped[str] = mapped_column(String(16), index=True)  # YYYY-MM-DD
    content_md: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"))
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    task_id: Mapped[str] = mapped_column(String(32), ForeignKey("tasks.id"))
    action_desc: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(16), default="high")
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    decided_by: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[float] = mapped_column(Float, default=now)


class AuditLog(Base):
    """Append-only reasoning-action log."""

    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    task_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    step: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    input_digest: Mapped[str] = mapped_column(String(512), default="")
    output_digest: Mapped[str] = mapped_column(String(512), default="")
    cached: Mapped[int] = mapped_column(Integer, default=0)
    simulated: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[float] = mapped_column(Float, default=now, index=True)


class LlmCache(Base):
    __tablename__ = "llm_cache"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # normalized prompt hash
    response: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64), default="")
    expires_at: Mapped[float] = mapped_column(Float, default=0)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Setting(Base):
    """Business-level config, hot-tunable from the Web UI."""

    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)


Index("ix_tasks_queue", Task.status, Task.priority, Task.created_at)
