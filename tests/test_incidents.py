"""The incident state machine driven by the checker (Beat 2.1)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from beacon.checker import Checker
from beacon.models import Monitor, Outcome
from beacon.storage import InMemoryStorage
from tests.conftest import FakeProber

NOW = datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC)
URL = "https://t.example"


def _monitor(storage: InMemoryStorage) -> Monitor:
    return storage.create_monitor(
        Monitor(name="t", url=URL, interval_seconds=60, timeout_seconds=10)
    )


def _probe(checker: Checker, prober: FakeProber, *, at: datetime, ok: bool) -> None:
    prober.set(URL, Outcome(ok=ok, status_code=200 if ok else 500, checked_at=at))
    asyncio.run(checker.tick(at))


def _sequence(threshold: int, oks: list[bool]) -> InMemoryStorage:
    storage = InMemoryStorage()
    prober = FakeProber()
    _monitor(storage)
    checker = Checker(storage, prober, incident_failure_threshold=threshold)
    for i, ok in enumerate(oks):
        _probe(checker, prober, at=NOW + timedelta(seconds=60 * i), ok=ok)
    return storage


def test_no_incident_below_threshold() -> None:
    storage = _sequence(3, [False, False])
    assert storage.list_incidents() == []


def test_incident_opens_at_threshold_backdated_to_first_failure() -> None:
    storage = _sequence(3, [True, False, False, False])
    incidents = storage.list_incidents()
    assert len(incidents) == 1
    # first failure was the second probe, at NOW + 60s
    assert incidents[0].opened_at == NOW + timedelta(seconds=60)
    assert incidents[0].is_open


def test_incident_closes_on_first_success() -> None:
    storage = _sequence(3, [False, False, False, True])
    incident = storage.list_incidents()[0]
    assert not incident.is_open
    assert incident.resolved_at == NOW + timedelta(seconds=180)


def test_flap_never_reaches_threshold() -> None:
    storage = _sequence(3, [False, False, True, False, False])
    assert storage.list_incidents() == []


def test_only_one_incident_while_failures_continue() -> None:
    storage = _sequence(3, [False, False, False, False, False])
    incidents = storage.list_incidents()
    assert len(incidents) == 1
    assert incidents[0].opened_at == NOW


def test_recovery_then_new_outage_opens_a_second_incident() -> None:
    storage = _sequence(3, [False, False, False, True, False, False, False])
    incidents = storage.list_incidents()  # newest first
    assert len(incidents) == 2
    assert incidents[0].opened_at == NOW + timedelta(seconds=240)
    assert incidents[1].resolved_at == NOW + timedelta(seconds=180)
