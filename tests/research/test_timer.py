import time

from adaptron.research.timer import TimeBudgetWrapper


def test_timer_starts_and_checks():
    timer = TimeBudgetWrapper(time_budget=10)
    timer.start()
    assert timer.is_expired() is False
    assert timer.elapsed() >= 0
    assert timer.remaining() <= 10


def test_timer_expires():
    timer = TimeBudgetWrapper(time_budget=0)
    timer.start()
    time.sleep(0.01)
    assert timer.is_expired() is True


def test_timer_not_started():
    timer = TimeBudgetWrapper(time_budget=300)
    assert timer.elapsed() == 0.0
    assert timer.is_expired() is False


def test_timer_remaining():
    timer = TimeBudgetWrapper(time_budget=5)
    timer.start()
    remaining = timer.remaining()
    assert 0 <= remaining <= 5
