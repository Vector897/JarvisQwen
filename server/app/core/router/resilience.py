"""弹性容错：带抖动的指数退避 + 断路器 + fallback 链编排。

对应调研报告《断点续传与任务重跑》第三章：Exponential Backoff with Jitter、
Circuit Breakers、多备份模型策略。
"""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from typing import Callable, TypeVar

T = TypeVar("T")


class CircuitBreaker:
    """滑动窗口失败率断路器（每个 厂商/模型 一个实例）。

    closed（正常）→ 窗口内失败率超阈值 → open（熔断，直接拒绝）
    → 冷却期后 half-open（放一个探测请求）→ 成功恢复 closed / 失败回到 open。
    """

    def __init__(self, window: int = 10, threshold: float = 0.6, cooldown: float = 60.0) -> None:
        self.window = window
        self.threshold = threshold
        self.cooldown = cooldown
        self.results: deque[bool] = deque(maxlen=window)
        self.opened_at: float = 0.0
        self.state = "closed"
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            if self.state == "open":
                if time.time() - self.opened_at >= self.cooldown:
                    self.state = "half-open"
                    return True  # 放一个探测请求
                return False
            return True

    def report(self, success: bool) -> None:
        with self._lock:
            self.results.append(success)
            if self.state == "half-open":
                if success:
                    self.state = "closed"
                    self.results.clear()
                else:
                    self.state = "open"
                    self.opened_at = time.time()
                return
            if len(self.results) >= self.window:
                failure_rate = 1 - sum(self.results) / len(self.results)
                if failure_rate >= self.threshold:
                    self.state = "open"
                    self.opened_at = time.time()


_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def breaker_for(name: str) -> CircuitBreaker:
    with _breakers_lock:
        if name not in _breakers:
            _breakers[name] = CircuitBreaker()
        return _breakers[name]


class AllModelsFailed(Exception):
    pass


def backoff_delays(retries: int, base: float = 1.0, cap: float = 30.0) -> list[float]:
    """指数退避 + 全抖动：delay = random(0, min(cap, base*2^i))。"""
    return [random.uniform(0, min(cap, base * (2**i))) for i in range(retries)]


def call_with_fallbacks(
    models: list[str],
    fn: Callable[[str], T],
    retries_per_model: int = 2,
    is_retryable: Callable[[Exception], bool] | None = None,
) -> tuple[str, T]:
    """沿 fallback 链依次尝试各模型，每个模型内部做退避重试。返回 (成功的模型, 结果)。"""
    is_retryable = is_retryable or (lambda e: True)
    last_error: Exception | None = None
    for model in models:
        br = breaker_for(model)
        if not br.allow():
            continue  # 熔断中，跳到下一个备份模型
        delays = backoff_delays(retries_per_model)
        for attempt in range(retries_per_model + 1):
            try:
                result = fn(model)
                br.report(True)
                return model, result
            except Exception as e:  # noqa: BLE001
                br.report(False)
                last_error = e
                if attempt < retries_per_model and is_retryable(e):
                    time.sleep(delays[attempt])
                else:
                    break  # 不可重试或次数用尽 → 换下一个模型
    raise AllModelsFailed(f"All models failed; last error: {last_error}")
