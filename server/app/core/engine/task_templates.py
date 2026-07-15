"""Task templates: fill-in-the-blank ready-to-use for common monitoring scenarios, lowering the barrier to creating tasks in natural language.

The template wording targets the general pattern of "knowledge-work monitoring"; the current connectors are arXiv/Semantic Scholar
(covering disciplines such as CS/physics/math/finance/biology/engineering), and other information sources extend along the same graph structure.

Display strings (name/description/field label/placeholder) are bilingual: the API localizes them per request language via
``localized_templates(lang)``. Functional keys (id/task_type/field key/type/default) stay language-independent.
"""
from __future__ import annotations


def _L(en: str, zh: str) -> dict:
    """A bilingual display string. Resolved to one language by ``_pick`` at request time."""
    return {"en": en, "zh": zh}


TEMPLATES = [
    {
        "id": "literature_watch",
        "name": _L("Topic watch", "主题追踪"),
        "description": _L(
            "Continuously monitor new publications on any topic — AI, finance, "
            "biology, engineering — auto-triage, deep-summarize, archive, brief",
            "持续追踪任意主题的新成果——AI、金融、生物、工程——自动初筛、精读摘要、归档、生成简报",
        ),
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "type": "text",
             "label": _L("Topic keywords", "主题关键词"),
             "placeholder": _L("e.g. LLM agent security / portfolio optimization",
                               "如 LLM agent security / 投资组合优化")},
            {"key": "max_results", "type": "number", "default": 15,
             "label": _L("Papers per poll", "每轮抓取篇数")},
        ],
    },
    {
        "id": "security_watch",
        "name": _L("Security watch", "安全追踪"),
        "description": _L(
            "Track security research the way an on-call team tracks advisories — "
            "new attack & defense work on your stack, triaged and summarized",
            "像值班团队盯安全通告一样追踪安全研究——你技术栈上的新攻防工作,自动初筛并摘要",
        ),
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "type": "text",
             "label": _L("What to guard", "关注的防护面"),
             "placeholder": _L("e.g. prompt injection defense / container escape",
                               "如 提示注入防御 / 容器逃逸")},
            {"key": "max_results", "type": "number", "default": 15,
             "label": _L("Papers per poll", "每轮抓取篇数")},
        ],
    },
    {
        "id": "market_watch",
        "name": _L("Market & finance watch", "市场与金融追踪"),
        "description": _L(
            "Track markets both ways — breaking financial news (stocks, earnings, "
            "M&A) and quantitative finance preprints — triaged and briefed every morning",
            "双向追踪市场——突发财经新闻(股票、财报、并购)与量化金融预印本——每早初筛并生成简报",
        ),
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "type": "text",
             "label": _L("Market topic or ticker", "市场主题或股票代码"),
             "placeholder": _L("e.g. Micron MU stock / portfolio optimization",
                               "如 美光 MU 股票 / 投资组合优化")},
            {"key": "max_results", "type": "number", "default": 15,
             "label": _L("Items per poll", "每轮抓取条数")},
        ],
    },
    {
        "id": "proposal_research",
        "name": _L("Deep-dive survey", "深度调研"),
        "description": _L(
            "One focused sweep over a specific question — search wide, triage, "
            "summarize everything relevant. Great before starting a project",
            "针对一个具体问题做一次集中扫描——广泛检索、初筛、把相关内容全部摘要。开题前很好用",
        ),
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "type": "text",
             "label": _L("Research question", "研究问题"),
             "placeholder": _L("e.g. catastrophic forgetting in multi-agent RL",
                               "如 多智能体强化学习中的灾难性遗忘")},
            {"key": "max_results", "type": "number", "default": 30,
             "label": _L("Papers to sweep (go big)", "扫描篇数(可以大胆调大)")},
        ],
    },
    {
        "id": "weekly_briefing",
        "name": _L("Briefing now", "立即生成简报"),
        "description": _L(
            "Don't wait for tomorrow morning — aggregate the last 24h of "
            "summaries into a briefing right now",
            "不必等到明早——现在就把过去 24 小时的摘要汇总成一份简报",
        ),
        "task_type": "briefing",
        "fields": [],
    },
]


def _pick(value, lang: str):
    """Resolve a bilingual dict to one language; pass through plain values unchanged."""
    if isinstance(value, dict) and ("en" in value or "zh" in value):
        return value.get(lang) or value.get("en") or ""
    return value


def localized_templates(lang: str = "en") -> list[dict]:
    """Return templates with display strings resolved to ``lang`` (functional keys untouched)."""
    out = []
    for t in TEMPLATES:
        out.append({
            "id": t["id"],
            "name": _pick(t["name"], lang),
            "description": _pick(t["description"], lang),
            "task_type": t["task_type"],
            "fields": [
                {k: (_pick(v, lang) if k in ("label", "placeholder") else v)
                 for k, v in f.items()}
                for f in t["fields"]
            ],
        })
    return out


def apply_template(template_id: str, values: dict) -> tuple[str, dict, str]:
    tpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if tpl is None:
        raise ValueError(f"Unknown template: {template_id}")
    params = {}
    for f in tpl["fields"]:
        val = values.get(f["key"], f.get("default", ""))
        if f["type"] == "text" and not str(val).strip():
            # text fields without a default are required: an empty query makes the arXiv API error out directly and the task is bound to fail
            raise ValueError(f"Field '{_pick(f['label'], 'en')}' is required")
        params[f["key"]] = val
    title = f"{_pick(tpl['name'], 'en')}: {params.get('query', '')}".strip(": ")[:60]
    return tpl["task_type"], params, title
