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
    # 三级路由的模型选择——默认 Qwen 全家桶：规则层 $0 → flash 初筛 → max 深度总结
    "model_light": "qwen/qwen3.6-flash",
    "model_light_fallbacks": ["qwen/qwen3.7-plus"],
    "model_frontier": "qwen/qwen3.7-max",
    "model_frontier_fallbacks": ["qwen/qwen3.7-plus"],
    "max_retries": 3,
    "relevance_threshold": 0.5,  # 论文初筛相关度阈值
    "research_profile": "",  # 用户研究方向描述，用于初筛与总结的上下文
    "cascade_enabled": True,
    "cascade_confidence_threshold": 0.6,
    # 推送通知
    "notify_telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "notify_email_enabled": False,
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
    "smtp_to": "",
    "notify_on_budget_cutoff": True,
    # Zotero 同步
    "zotero_api_key": "",
    "zotero_library_id": "",
    "zotero_library_type": "user",
    # 界面
    "ui_theme": "light",  # light/dark（也存一份在 localStorage，这里做跨设备记忆）
    "ui_lang": "en",  # en/zh
}

SECRET_KEYS = {  # 这些 key 在 GET /api/settings 中掩码返回，避免明文泄露给前端
    "telegram_bot_token", "smtp_password", "zotero_api_key",
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


def all_settings(db: Session, mask_secrets: bool = False) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    for row in db.execute(select(Setting)).scalars():
        try:
            merged[row.key] = json.loads(row.value_json)
        except json.JSONDecodeError:
            pass
    if mask_secrets:
        # 密钥字段不回显明文：置空 + 附带 "<key>_is_set" 布尔位。
        # 前端：字段留空提交 = 不改动既有密钥（PUT 时跳过空的 secret 字段）。
        for key in SECRET_KEYS:
            merged[f"{key}_is_set"] = bool(merged.get(key))
            merged[key] = ""
    return merged
