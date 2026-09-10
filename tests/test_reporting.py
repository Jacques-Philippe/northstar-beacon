"""Uptime and status derived from incidents (Beat 2.1)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from beacon.models import Incident, Monitor
from beacon.reporting import monitor_uptime, status_report
from beacon.storage import InMemoryStorage

NOW = datetime(2026, 9, 10, 12, 0, 0, tzinfo=UTC)


def _monitor(storage: InMemoryStorage, **kw: object) -> Monitor:
    defaults = dict(name="t", url="https://t.example", interval_seconds=60, timeout_seconds=10)
    return storage.create_monitor(Monitor(**{**defaults, **kw}))


def test_no_incidents_is_100_percent() -> None:
    storage = InMemoryStorage()
    m = _monitor(storage)
    u = monitor_uptime(storage, m.id, now=NOW)
    assert u.day.uptime_percent == 100.0
    assert u.week.uptime_percent == 100.0
    assert u.day.downtime_seconds == 0.0


def test_closed_incident_inside_the_day_window() -> None:
    storage = InMemoryStorage()
    m = _monitor(storage)
    storage.add_incident(
        Incident(
            monitor_id=m.id,
            opened_at=NOW - timedelta(hours=3),
            resolved_at=NOW - timedelta(hours=2),
        )
    )
    u = monitor_uptime(storage, m.id, now=NOW)
    assert u.day.downtime_seconds == 3600.0
    assert u.day.uptime_percent == round((86400 - 3600) / 86400 * 100, 4)
    # same hour is a much smaller slice of the week
    assert u.week.downtime_seconds == 3600.0


def test_open_incident_counts_up_to_now() -> None:
    storage = InMemoryStorage()
    m = _monitor(storage)
    storage.add_incident(Incident(monitor_id=m.id, opened_at=NOW - timedelta(minutes=30)))
    u = monitor_uptime(storage, m.id, now=NOW)
    assert u.day.downtime_seconds == 1800.0


def test_incident_straddling_the_week_boundary_is_clipped() -> None:
    storage = InMemoryStorage()
    m = _monitor(storage)
    storage.add_incident(
        Incident(
            monitor_id=m.id,
            opened_at=NOW - timedelta(days=9),
            resolved_at=NOW - timedelta(days=6),
        )
    )
    u = monitor_uptime(storage, m.id, now=NOW)
    # only the 1 day that falls inside the 7-day window counts
    assert u.week.downtime_seconds == 86400.0


def test_status_report_tallies_by_current_state() -> None:
    from beacon.models import CheckResult

    storage = InMemoryStorage()
    up = _monitor(storage, name="up")
    down = _monitor(storage, name="down", owning_team="platform")
    _monitor(storage, name="never-probed")

    storage.append_result(CheckResult(monitor_id=up.id, ok=True, checked_at=NOW))
    storage.append_result(CheckResult(monitor_id=down.id, ok=False, checked_at=NOW))
    storage.add_incident(Incident(monitor_id=down.id, opened_at=NOW - timedelta(minutes=5)))

    report = status_report(storage, now=NOW)
    assert (report.total, report.up, report.down, report.unknown) == (3, 1, 1, 1)
    assert report.open_incidents == 1
    line = next(m for m in report.monitors if m.name == "down")
    assert line.owning_team == "platform"
    assert line.open_since == NOW - timedelta(minutes=5)
