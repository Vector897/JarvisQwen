"""BYOK：API Key 归一化、厂商识别、加密存取、探活校验、多 Key 选择。"""
from __future__ import annotations

import base64
import hashlib
import re
import unicodedata

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import config
from ...models import ApiKey

PROVIDERS = ["qwen", "anthropic", "openai", "google", "deepseek", "openrouter", "custom"]

# Qwen Cloud（DashScope 国际站）OpenAI 兼容端点——本项目的默认执行平面
QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# 厂商 -> LiteLLM 需要的环境变量名
ENV_VAR = {
    "qwen": "DASHSCOPE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _fernet() -> Fernet:
    digest = hashlib.sha256(config.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_key(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_key(enc: str) -> str:
    return _fernet().decrypt(enc.encode()).decode()


def normalize_key(raw: str) -> str:
    """自动格式修正：去空白/换行/引号/Bearer 前缀/变量名残留，全角转半角。"""
    s = unicodedata.normalize("NFKC", raw)  # 全角 → 半角
    s = s.strip().strip("'\"`").strip()
    s = re.sub(r"^(?:Bearer|bearer)\s+", "", s)
    s = re.sub(r"^[A-Z_]*API_?KEY\s*[=:]\s*", "", s, flags=re.IGNORECASE)
    s = "".join(s.split())  # 去除内部换行与空格（key 内不含空白）
    return s.strip("'\"`")


def detect_provider(key: str, base_url: str = "") -> str:
    """按前缀识别厂商；识别不了返回空串让用户手选。"""
    if base_url:
        return "custom"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("sk-or-"):
        return "openrouter"
    if key.startswith("AIza"):
        return "google"
    if key.startswith("sk-proj-") or key.startswith("sk-svcacct-"):
        return "openai"
    if key.startswith("sk-") and len(key) >= 35 and len(key) <= 60:
        return ""  # Qwen / OpenAI / DeepSeek 前缀相同，需用户确认
    return ""


def mask(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return f"{key[:6]}***{key[-4:]}"


def probe(provider: str, key: str, base_url: str = "") -> tuple[bool, str]:
    """实时探活：发一次最小请求，返回 (可用, 人话消息)。"""
    try:
        import litellm

        model = {
            "qwen": "openai/qwen3.6-flash",
            "anthropic": "anthropic/claude-haiku-4-5-20251001",
            "openai": "openai/gpt-4o-mini",
            "google": "gemini/gemini-2.0-flash",
            "deepseek": "deepseek/deepseek-chat",
            "openrouter": "openrouter/openai/gpt-4o-mini",
        }.get(provider, "openai/gpt-4o-mini")
        kwargs: dict = {"api_key": key, "max_tokens": 1, "timeout": 20}
        if provider == "qwen" and not base_url:
            base_url = QWEN_BASE_URL
        if base_url:
            kwargs["api_base"] = base_url
            model = "openai/" + model.split("/", 1)[-1]
        litellm.completion(model=model, messages=[{"role": "user", "content": "ping"}], **kwargs)
        return True, "Key 可用 ✅"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "401" in msg or "invalid" in msg.lower() or "authentication" in msg.lower():
            return False, "Key 无效（认证失败），请检查是否复制完整"
        if "quota" in msg.lower() or "insufficient" in msg.lower() or "balance" in msg.lower():
            return False, "Key 有效但余额/配额不足"
        if "429" in msg:
            return True, "Key 可用，但当前处于限流状态"
        return False, f"校验失败：{msg[:160]}"


def pick_key(db: Session, provider: str) -> ApiKey | None:
    """按优先级选一个 active 的 Key（断路器把坏 Key 置为 broken/rate_limited）。"""
    return db.execute(
        select(ApiKey)
        .where(ApiKey.provider == provider, ApiKey.status == "active")
        .order_by(ApiKey.priority)
    ).scalars().first()


def provider_of_model(model: str) -> str:
    """LiteLLM 模型名前缀 -> 厂商。"""
    prefix = model.split("/", 1)[0]
    return {"gemini": "google", "vertex_ai": "google"}.get(prefix, prefix)


def litellm_route(model: str, key_row: ApiKey) -> tuple[str, str]:
    """把内部模型名转成 (LiteLLM 调用名, api_base)。

    qwen/* 走 Qwen Cloud 的 OpenAI 兼容端点（openai/ 前缀 + base_url）；
    其余厂商用 LiteLLM 原生前缀，api_base 仅在用户自定义端点时设置。
    """
    if provider_of_model(model) == "qwen":
        return "openai/" + model.split("/", 1)[-1], key_row.base_url or QWEN_BASE_URL
    return model, key_row.base_url or ""
