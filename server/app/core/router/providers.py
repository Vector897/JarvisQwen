"""BYOK: API key normalization, provider detection, encrypted storage, liveness validation, multi-key selection."""
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

# Qwen Cloud (DashScope international site) OpenAI-compatible endpoint — this project's default execution plane
QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Provider -> environment variable name required by LiteLLM
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
    """Automatic format cleanup: strip whitespace/newlines/quotes/Bearer prefix/leftover variable names, and convert full-width to half-width."""
    s = unicodedata.normalize("NFKC", raw)  # full-width → half-width
    s = s.strip().strip("'\"`").strip()
    s = re.sub(r"^(?:Bearer|bearer)\s+", "", s)
    s = re.sub(r"^[A-Z_]*API_?KEY\s*[=:]\s*", "", s, flags=re.IGNORECASE)
    s = "".join(s.split())  # remove internal newlines and spaces (keys contain no whitespace)
    return s.strip("'\"`")


def detect_provider(key: str, base_url: str = "") -> str:
    """Detect the provider by key prefix; return an empty string when undetectable so the user can pick manually."""
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
        return ""  # Qwen / OpenAI / DeepSeek share the same prefix; requires user confirmation
    return ""


def mask(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return f"{key[:6]}***{key[-4:]}"


def probe(provider: str, key: str, base_url: str = "") -> tuple[bool, str]:
    """Live liveness check: send one minimal request, return (usable, human-readable message)."""
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
        return True, "Key valid ✅"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "401" in msg or "invalid" in msg.lower() or "authentication" in msg.lower():
            return False, "Invalid key (authentication failed) - check that it was copied in full"
        if "quota" in msg.lower() or "insufficient" in msg.lower() or "balance" in msg.lower():
            return False, "Key valid but out of quota/balance"
        if "429" in msg:
            return True, "Key valid, currently rate-limited"
        return False, f"Validation failed: {msg[:160]}"


def import_env_keys() -> None:
    """On startup, automatically import DASHSCOPE_API_KEY from environment variables / .env
    (zero-click key configuration for cloud deployments).

    Lookup order: process environment variables → working directory .env → repo root ../.env.
    Skips insertion if an identical qwen key already exists, avoiding duplicate rows.
    """
    import os

    raw = os.environ.get("DASHSCOPE_API_KEY", "")
    if not raw:
        try:
            from dotenv import dotenv_values

            for env_path in (".env", "../.env"):
                raw = (dotenv_values(env_path).get("DASHSCOPE_API_KEY") or "").strip()
                if raw:
                    break
        except ImportError:
            return
    key = normalize_key(raw or "")
    if not key or len(key) < 10:
        return

    from ...db import session
    from ...models import User

    with session() as db:
        for row in db.execute(select(ApiKey).where(ApiKey.provider == "qwen")).scalars():
            if decrypt_key(row.encrypted_key) == key:
                return  # the same key is already in the database
        admin = db.execute(select(User).where(User.role == "admin")).scalars().first()
        if admin is None:
            return
        db.add(ApiKey(provider="qwen", encrypted_key=encrypt_key(key),
                      label="env:DASHSCOPE_API_KEY", owner_id=admin.id))
        print(f"[JarvisQwen] Imported Qwen Cloud API key from environment ({mask(key)})")


def pick_key(db: Session, provider: str) -> ApiKey | None:
    """Select one active key by priority (the circuit breaker marks bad keys as broken/rate_limited)."""
    return db.execute(
        select(ApiKey)
        .where(ApiKey.provider == provider, ApiKey.status == "active")
        .order_by(ApiKey.priority)
    ).scalars().first()


def provider_of_model(model: str) -> str:
    """LiteLLM model name prefix -> provider."""
    prefix = model.split("/", 1)[0]
    return {"gemini": "google", "vertex_ai": "google"}.get(prefix, prefix)


def litellm_route(model: str, key_row: ApiKey) -> tuple[str, str]:
    """Convert an internal model name into (LiteLLM call name, api_base).

    qwen/* goes through Qwen Cloud's OpenAI-compatible endpoint (openai/ prefix + base_url);
    other providers use LiteLLM's native prefix, with api_base set only for user-custom endpoints.
    """
    if provider_of_model(model) == "qwen":
        return "openai/" + model.split("/", 1)[-1], key_row.base_url or QWEN_BASE_URL
    return model, key_row.base_url or ""
