"""Resilience and fault tolerance: exponential backoff with jitter + circuit breaker + fallback chain orchestration.

Corresponds to Chapter 3 of the research report "Resumable Transfer and Task Rerun":
Exponential Backoff with Jitter, Circuit Breakers, and multi-backup model strategies.
"""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from typing import Callable, TypeVar

T = TypeVar("T")


class CircuitBreaker:
    """Sliding-window failure-rate circuit breaker (one instance per provider/model).

    closed (normal) → failure rate within the window exceeds threshold → open (tripped, reject directly)
    → after cooldown, half-open (let one probe request through) → success restores closed / failure returns to open.
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
                    return True  # let one probe request through
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
    """Exponential backoff + full jitter: delay = random(0, min(cap, base*2^i))."""
    return [random.uniform(0, min(cap, base * (2**i))) for i in range(retries)]


def call_with_fallbacks(
    models: list[str],
    fn: Callable[[str], T],
    retries_per_model: int = 2,
    is_retryable: Callable[[Exception], bool] | None = None,
) -> tuple[str, T]:
    """Try each model along the fallback chain in order, with backoff retries within each model. Returns (successful model, result)."""
    is_retryable = is_retryable or (lambda e: True)
    last_error: Exception | None = None
    for model in models:
        br = breaker_for(model)
        if not br.allow():
            continue  # tripped, skip to the next backup model
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
                    break  # not retryable or retries exhausted → move to the next model
    raise AllModelsFailed(f"All models failed; last error: {last_error}")
