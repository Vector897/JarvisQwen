"""Task templates: fill-in-the-blank ready-to-use for common monitoring scenarios, lowering the barrier to creating tasks in natural language.

The template wording targets the general pattern of "knowledge-work monitoring"; the current connectors are arXiv/Semantic Scholar
(covering disciplines such as CS/physics/math/finance/biology/engineering), and other information sources extend along the same graph structure.
"""
from __future__ import annotations

TEMPLATES = [
    {
        "id": "literature_watch",
        "name": "Topic watch",
        "description": "Continuously monitor new publications on any topic — AI, finance, "
                       "biology, engineering — auto-triage, deep-summarize, archive, brief",
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "label": "Topic keywords", "type": "text",
             "placeholder": "e.g. LLM agent security / portfolio optimization"},
            {"key": "max_results", "label": "Papers per poll", "type": "number", "default": 15},
        ],
    },
    {
        "id": "security_watch",
        "name": "Security watch",
        "description": "Track security research the way an on-call team tracks advisories — "
                       "new attack & defense work on your stack, triaged and summarized",
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "label": "What to guard", "type": "text",
             "placeholder": "e.g. prompt injection defense / container escape"},
            {"key": "max_results", "label": "Papers per poll", "type": "number", "default": 15},
        ],
    },
    {
        "id": "market_watch",
        "name": "Market & finance watch",
        "description": "Track markets both ways — breaking financial news (stocks, earnings, "
                       "M&A) and quantitative finance preprints — triaged and briefed every morning",
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "label": "Market topic or ticker", "type": "text",
             "placeholder": "e.g. Micron MU stock / portfolio optimization"},
            {"key": "max_results", "label": "Items per poll", "type": "number", "default": 15},
        ],
    },
    {
        "id": "proposal_research",
        "name": "Deep-dive survey",
        "description": "One focused sweep over a specific question — search wide, triage, "
                       "summarize everything relevant. Great before starting a project",
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "label": "Research question", "type": "text",
             "placeholder": "e.g. catastrophic forgetting in multi-agent RL"},
            {"key": "max_results", "label": "Papers to sweep (go big)", "type": "number", "default": 30},
        ],
    },
    {
        "id": "weekly_briefing",
        "name": "Briefing now",
        "description": "Don't wait for tomorrow morning — aggregate the last 24h of "
                       "summaries into a briefing right now",
        "task_type": "briefing",
        "fields": [],
    },
]


def apply_template(template_id: str, values: dict) -> tuple[str, dict, str]:
    tpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if tpl is None:
        raise ValueError(f"Unknown template: {template_id}")
    params = {}
    for f in tpl["fields"]:
        val = values.get(f["key"], f.get("default", ""))
        if f["type"] == "text" and not str(val).strip():
            # text fields without a default are required: an empty query makes the arXiv API error out directly and the task is bound to fail
            raise ValueError(f"Field '{f['label']}' is required")
        params[f["key"]] = val
    title = f"{tpl['name']}: {params.get('query', '')}".strip(": ")[:60]
    return tpl["task_type"], params, title
