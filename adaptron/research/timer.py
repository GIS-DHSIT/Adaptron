from __future__ import annotations

import time


class TimeBudgetWrapper:
    def __init__(self, time_budget: int) -> None:
        self._time_budget = time_budget
        self._start_time: float | None = None

    def start(self) -> None:
        self._start_time = time.monotonic()

    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def remaining(self) -> float:
        return max(0.0, self._time_budget - self.elapsed())

    def is_expired(self) -> bool:
        if self._start_time is None:
            return False
        return self.elapsed() >= self._time_budget
