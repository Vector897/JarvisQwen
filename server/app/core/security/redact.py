"""出境脱敏网关：三层检测堆栈（正则 → 熵 → 可选 NER），占位符映射与还原。

对应调研报告《敏感数据管理与脱敏》：Tier1 确定性正则、Tier2 香农熵、Tier3 NER（Presidio 可选安装）。
默认修改模式（替换占位符，返回后还原）；redact_level=high 时对高危命中直接阻断（验证模式）。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ---- Tier 1: 确定性正则 ----
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("PHONE_CN", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("ID_CN", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),  # 身份证
    ("CREDIT_CARD", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("API_KEY", re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}\b")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("IP", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")),
]
HIGH_RISK = {"API_KEY", "AWS_KEY", "ID_CN", "CREDIT_CARD"}

# ---- Tier 2: 熵检测（无固定格式的密钥/令牌）----
TOKEN_RE = re.compile(r"\b[A-Za-z0-9+/_=-]{28,}\b")


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in freq.values())


@dataclass
class RedactionResult:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)  # placeholder -> original
    blocked: bool = False
    reason: str = ""

    def restore(self, text: str) -> str:
        for ph, original in self.mapping.items():
            text = text.replace(ph, original)
        return text


def redact(text: str, level: str = "medium") -> RedactionResult:
    if level == "low":
        # 低等级只拦截明确的凭证
        active = [(n, p) for n, p in PATTERNS if n in ("API_KEY", "AWS_KEY")]
    else:
        active = PATTERNS

    mapping: dict[str, str] = {}
    counters: dict[str, int] = {}

    def replace(name: str, match: re.Match) -> str:
        original = match.group(0)
        for ph, ori in mapping.items():
            if ori == original:
                return ph
        counters[name] = counters.get(name, 0) + 1
        ph = f"[{name}_{counters[name]}]"
        mapping[ph] = original
        return ph

    high_risk_hit = False
    for name, pattern in active:
        if pattern.search(text) and name in HIGH_RISK:
            high_risk_hit = True
        text = pattern.sub(lambda m, n=name: replace(n, m), text)

    if level in ("medium", "high"):
        for m in list(TOKEN_RE.finditer(text)):
            token = m.group(0)
            if token.startswith("[") or shannon_entropy(token) < 4.2:
                continue
            high_risk_hit = True
            counters["SECRET"] = counters.get("SECRET", 0) + 1
            ph = f"[SECRET_{counters['SECRET']}]"
            mapping[ph] = token
            text = text.replace(token, ph)

    if level == "high" and high_risk_hit:
        return RedactionResult(text="", mapping={}, blocked=True, reason="检测到高危敏感数据，已按验证模式阻断出境")

    # Tier 3: Presidio NER（可选依赖，装了才启用）
    try:
        from presidio_analyzer import AnalyzerEngine  # type: ignore

        analyzer = AnalyzerEngine()
        for r in sorted(analyzer.analyze(text=text, language="en"), key=lambda x: -x.start):
            if r.entity_type in ("PERSON", "LOCATION") and r.score > 0.8:
                original = text[r.start : r.end]
                counters[r.entity_type] = counters.get(r.entity_type, 0) + 1
                ph = f"[{r.entity_type}_{counters[r.entity_type]}]"
                mapping[ph] = original
                text = text[: r.start] + ph + text[r.end :]
    except ImportError:
        pass

    return RedactionResult(text=text, mapping=mapping)
