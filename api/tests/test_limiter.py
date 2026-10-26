import pytest

from emberline.data.limiter import RateLimiter


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.now += s


async def test_allows_up_to_max_without_waiting() -> None:
    t = FakeTime()
    lim = RateLimiter(3, 10, t.clock, t.sleep)
    for _ in range(3):
        await lim.acquire()
    assert t.slept == [] and lim.in_window == 3


async def test_waits_for_oldest_call_to_expire() -> None:
    t = FakeTime()
    lim = RateLimiter(2, 10, t.clock, t.sleep)
    await lim.acquire()
    t.now = 4
    await lim.acquire()
    await lim.acquire()  # must wait until t=10
    assert t.slept == [pytest.approx(6.0)]
    assert t.now == pytest.approx(10.0)


async def test_window_slides() -> None:
    t = FakeTime()
    lim = RateLimiter(1, 5, t.clock, t.sleep)
    await lim.acquire()
    t.now = 6
    await lim.acquire()
    assert t.slept == []


def test_rejects_bad_limit() -> None:
    with pytest.raises(ValueError):
        RateLimiter(0)
