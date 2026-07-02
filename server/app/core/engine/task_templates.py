"""任务模板：常见科研场景填空即用，降低自然语言下任务的门槛。"""
from __future__ import annotations

TEMPLATES = [
    {
        "id": "literature_watch",
        "name": "文献跟踪",
        "description": "持续监控某个研究方向的新论文，自动总结归档",
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "label": "研究方向关键词", "type": "text",
             "placeholder": "如：counterfactual regret minimization"},
            {"key": "max_results", "label": "单次检索篇数", "type": "number", "default": 15},
        ],
    },
    {
        "id": "proposal_research",
        "name": "开题调研",
        "description": "针对一个具体课题做一轮集中检索与总结，适合开题前快速摸底",
        "task_type": "arxiv_watch",
        "fields": [
            {"key": "query", "label": "课题描述", "type": "text",
             "placeholder": "如：多智能体强化学习中的灾难性遗忘"},
            {"key": "max_results", "label": "检索篇数（建议调大）", "type": "number", "default": 30},
        ],
    },
    {
        "id": "weekly_briefing",
        "name": "立即生成简报",
        "description": "不等到明天早晨，立刻汇总近 24 小时的总结生成一份简报",
        "task_type": "briefing",
        "fields": [],
    },
]


def apply_template(template_id: str, values: dict) -> tuple[str, dict, str]:
    tpl = next((t for t in TEMPLATES if t["id"] == template_id), None)
    if tpl is None:
        raise ValueError(f"未知模板：{template_id}")
    params = {}
    for f in tpl["fields"]:
        params[f["key"]] = values.get(f["key"], f.get("default", ""))
    title = f"{tpl['name']}：{params.get('query', '')}"[:60]
    return tpl["task_type"], params, title
