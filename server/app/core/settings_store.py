"""业务级配置（settings 表）读写，Web 端改完即热生效。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import config
from ..models import Setting

DEFAULTS: dict[str, Any] = {
    "daily_budget_usd": config.daily_budget_usd,
    "redact_level": "medium",  # low/medium/high；high=验证模式直接阻断
    "cache_enabled": True,
    "cache_ttl_hours": 72,
    "briefing_hour": 7,  # 每天几点生成简报
    "consolidate_hour": 3,  # 记忆整合时间
    # 三级路由的模型选择（LiteLLM 模型名）
    "model_light": "gemini/gemini-2.0-flash",
    "model_light_fallbacks": ["anthropic/claude-haiku-4-5-20251001", "deepseek/deepseek-chat"],
    "model_frontier": "anthropic/claude-sonnet-5",
    "model_frontier_fallbacks": ["openai/gpt-5", "gemini/gemini-2.5-pro"],
    "max_retries": 3,
    "relevance_threshold": 0.5,  # 论文初筛相关度阈值
    "research_profile": "",  # 用户研究方向描述，用于初筛与总结的上下文
}


def get_setting(db: Session, key: str) -> Any:
    row = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if row is None:
        return DEFAULTS.get(key)
    return json.loads(row.value_json)


def set_setting(db: Session, key: str, value: Any) -> None:
    row = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if row is None:
        db.add(Setting(key=key, value_json=json.dumps(value, ensure_ascii=False)))
    else:
        row.value_json = json.dumps(value, ensure_ascii=False)


def all_settings(db: Session) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    for row in db.execute(select(Setting)).scalars():
        try:
            merged[row.key] = json.loads(row.value_json)
        except json.JSONDecodeError:
            pass
    return merged
