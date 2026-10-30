"""Work nobody waits for pauses for real, so the threads that are waiting get through (the hub's Pacer).

Measured with a busy thread beside one making 3,000 stat calls: 8.1 s against 4 ms idle; ``sleep(0)``
every 200 items changed nothing (7.4 s); a 2 ms pause after each 30 ms of work cost the busy thread
about 6% and brought the other to 35 ms.

Fully offline.
"""
from __future__ import annotations

import os
import threading
import time
from typing import List

import pytest

from hubofhubs.recall import background_pacing
from hubofhubs.recall.background_pacing import PAUSE_SECONDS, WORK_SECONDS, Pacer


class FakeClock:
    """A clock the test advances itself, and a sleep that records the pauses instead of taking them."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.pauses: List[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.pauses.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(background_pacing.time, "monotonic", fake.monotonic)
    monkeypatch.setattr(background_pacing.time, "sleep", fake.sleep)
    return fake


def test_a_pacer_pauses_after_each_stretch_of_work(clock):
    pace = Pacer(work_seconds=1.0, pause_seconds=0.25)
    for _ in range(10):
        clock.now += 0.5
        pace()
    assert clock.pauses == [0.25] * 5


def test_the_default_stretch_and_pause_are_the_measured_ones(clock):
    pace = Pacer()
    clock.now += WORK_SECONDS / 2
    pace()
    assert clock.pauses == []
    clock.now += WORK_SECONDS
    pace()
    assert clock.pauses == [PAUSE_SECONDS]


def test_a_pacer_that_never_paces_never_sleeps(clock):
    pace = Pacer.never()
    for _ in range(10):
        clock.now += WORK_SECONDS * 3
        pace()
    assert clock.pauses == []


def test_a_pacer_stays_out_of_the_way_until_its_start_time(clock):
    pace = Pacer(start_after=clock.now + 5.0, work_seconds=2.0, pause_seconds=0.25)
    for _ in range(6):
        clock.now += 1.0
        pace()
    # Work before the start time does not count towards a pause: the first stretch begins when it passes.
    assert clock.pauses == [0.25]
    clock.now += 2.0
    pace()
    assert clock.pauses == [0.25, 0.25]



def blocking_calls(count: int) -> float:
    started = time.perf_counter()
    for _ in range(count):
        os.stat(".")
    return time.perf_counter() - started


def time_blocking_calls_beside_busy_thread(pace: Pacer, count: int = 150) -> float:
    stop = threading.Event()

    def busy() -> None:
        while not stop.is_set():
            sum(i * i for i in range(20000))
            pace()

    thread = threading.Thread(target=busy, daemon=True)
    thread.start()
    time.sleep(0.05)
    try:
        return blocking_calls(count)
    finally:
        stop.set()
        thread.join()


def test_a_paced_thread_leaves_the_others_their_blocking_calls():
    unpaced = time_blocking_calls_beside_busy_thread(Pacer.never())
    paced = time_blocking_calls_beside_busy_thread(Pacer())
    assert paced < unpaced / 4, f"paced {paced:.3f}s, unpaced {unpaced:.3f}s"
