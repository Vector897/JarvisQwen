"""append-only 推理-行动审计日志。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ...models import AuditLog


def _digest(text: str, limit: int = 300) -> str:
    text = text.replace("\n", " ").strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def record(
    db: Session,
    *,
    task_id: str = "",
    step: str = "",
    model: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    input_text: str = "",
    output_text: str = "",
    cached: bool = False,
    simulated: bool = False,
) -> None:
    db.add(
        AuditLog(
            task_id=task_id,
            step=step,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            input_digest=_digest(input_text),
            output_digest=_digest(output_text),
            cached=1 if cached else 0,
            simulated=1 if simulated else 0,
        )
    )
