"""Egress redaction gateway: a three-tier detection stack (regex → entropy → optional NER), with placeholder mapping and restoration.

Corresponds to the research report "Sensitive Data Management and Redaction": Tier 1 deterministic regex, Tier 2 Shannon entropy, Tier 3 NER (Presidio, optionally installed).
Default modification mode (replace with placeholders, restore after the response returns); when redact_level=high, high-risk hits are blocked outright (validation mode).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# ---- Tier 1: deterministic regex ----
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("PHONE_CN", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("ID_CN", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),  # national ID card
    ("CREDIT_CARD", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("API_KEY", re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}\b")),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("IP", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")),
]
HIGH_RISK = {"API_KEY", "AWS_KEY", "ID_CN", "CREDIT_CARD"}

# ---- Tier 2: entropy detection (secrets/tokens without a fixed format) ----
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
        # The low level intercepts only explicit credentials
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
        return RedactionResult(text="", mapping={}, blocked=True, reason="High-risk sensitive data detected; egress blocked (strict mode)")

    # Tier 3: Presidio NER (optional dependency, enabled only when installed)
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
