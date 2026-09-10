from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from beacon.checker import Checker
from beacon.models import CheckResult, Monitor
from beacon.storage import InMemoryStorage
from tests.conftest import FakeProber

NOW = datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC)


def make(storage: InMemoryStorage, **overrides: object) -> Monitor:
    defaults = dict(name="t", url="https://t.example", interval_seconds=60, timeout_seconds=10)
    monitor = Monitor(**{**defaults, **overrides})
    return storage.create_monitor(monitor)


def test_tick_probes_a_monitor_never_checked() -> None:
    storage = InMemoryStorage()
    prober = FakeProber()
    monitor = make(storage)
    checker = Checker(storage, prober)

    asyncio.run(checker.tick(NOW))

    assert prober.calls == [monitor.url]
    assert storage.get_latest_result(monitor.id) is not None


def test_tick_skips_a_monitor_checked_within_its_interval() -> None:
    storage = InMemoryStorage()
    prober = FakeProber()
    monitor = make(storage, interval_seconds=60)
    storage.append_result(
        CheckResult(
            monitor_id=monitor.id, ok=True, status_code=200, checked_at=NOW - timedelta(seconds=30)
        )
    )
    checker = Checker(storage, prober)

    asyncio.run(checker.tick(NOW))

    assert prober.calls == []


def test_tick_probes_again_once_the_interval_has_elapsed() -> None:
    storage = InMemoryStorage()
    prober = FakeProber()
    monitor = make(storage, interval_seconds=60)
    storage.append_result(
        CheckResult(
            monitor_id=monitor.id, ok=True, status_code=200, checked_at=NOW - timedelta(seconds=90)
        )
    )
    checker = Checker(storage, prober)

    asyncio.run(checker.tick(NOW))

    assert prober.calls == [monitor.url]


def test_tick_skips_disabled_monitors() -> None:
    storage = InMemoryStorage()
    prober = FakeProber()
    make(storage, enabled=False)
    checker = Checker(storage, prober)

    asyncio.run(checker.tick(NOW))

    assert prober.calls == []


def test_run_stops_promptly_on_stop() -> None:
    storage = InMemoryStorage()
    checker = Checker(storage, FakeProber(), tick_seconds=10)

    async def scenario() -> None:
        task = asyncio.create_task(checker.run())
        await asyncio.sleep(0.05)
        checker.stop()
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(scenario())
