"""Deployment-level config: environment variables / .env. Business-level config (model, budget, redaction level) lives in the settings table and is hot-tunable from the Web UI."""
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
    web_origin: str = ""  # Vercel domain for mode B (CORS fallback)
    ratelimit_enabled: bool = True  # inbound rate limiting (guards public deployments against scanning/floods)
    ratelimit_rpm: int = 240        # per-minute request ceiling; normal use stays well below this
    access_code: str = ""           # when set, /api requires this access code (cookie/?k=/header); empty = fully open

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
