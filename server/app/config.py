"""部署级配置：环境变量 / .env。业务级配置（模型、预算、脱敏等级）在 settings 表，Web 热调。"""
from __future__ import annotations

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AAOS_", env_file=".env", extra="ignore")

    data_dir: Path = Path("./data")
    secret_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    daily_budget_usd: float = 2.0
    web_origin: str = ""  # 模式 B 的 Vercel 域名（CORS 兜底）

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'aaos.db'}"

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdfs"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        if not self.secret_key:
            keyfile = self.data_dir / "secret.key"
            if keyfile.exists():
                self.secret_key = keyfile.read_text().strip()
            else:
                self.secret_key = secrets.token_urlsafe(48)
                keyfile.write_text(self.secret_key)


config = Config()
