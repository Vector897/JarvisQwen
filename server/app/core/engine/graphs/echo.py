"""最简测试图：验证队列、引擎、检查点、SSE 全链路。"""
from __future__ import annotations

import time

from ..engine import StepDef, TaskContext, register


def step_one(ctx: TaskContext, state: dict) -> dict:
    time.sleep(1)
    state["msg"] = state["params"].get("message", "hello AAOS")
    ctx.artifact("回显输入", state["msg"])
    return state


def step_two(ctx: TaskContext, state: dict) -> dict:
    time.sleep(1)
    ctx.artifact("回显输出", f"echo: {state['msg']}")
    return state


register("echo", [
    StepDef("receive", step_one, default_duration=1.5),
    StepDef("echo", step_two, default_duration=1.5),
])
