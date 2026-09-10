"""Deriving uptime and current status from incidents.

Uptime is computed from :class:`Incident` records, not by scanning every ``CheckResult``:
an incident is an interval of known-bad time, so uptime over a window is one minus the
share of that window covered by incidents. The result stream stays available for detail
views, but the percentage never depends on its size.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel

from beacon.models import Incident, Monitor, Status, status_for
from beacon.storage.base import Storage

DAY = timedelta(days=1)
WEEK = timedelta(days=7)


class UptimeWindow(BaseModel):
    since: datetime
    until: datetime
    downtime_seconds: float
    uptime_percent: float


class MonitorUptime(BaseModel):
    monitor_id: str
    day: UptimeWindow
    week: UptimeWindow


class StatusLine(BaseModel):
    monitor_id: str
    name: str
    status: Status
    owning_team: str | None
    open_since: datetime | None


class StatusReport(BaseModel):
    generated_at: datetime
    total: int
    up: int
    down: int
    unknown: int
    open_incidents: int
    monitors: list[StatusLine]


def _window(incidents: list[Incident], since: datetime, until: datetime) -> UptimeWindow:
    span = (until - since).total_seconds()
    downtime = sum(i.downtime_within(since, until).total_seconds() for i in incidents)
    downtime = min(downtime, span)
    uptime = 100.0 if span <= 0 else (span - downtime) / span * 100
    return UptimeWindow(
        since=since,
        until=until,
        downtime_seconds=round(downtime, 3),
        uptime_percent=round(uptime, 4),
    )


def monitor_uptime(storage: Storage, monitor_id: str, *, now: datetime) -> MonitorUptime:
    incidents = storage.list_incidents(monitor_id=monitor_id, since=now - WEEK)
    return MonitorUptime(
        monitor_id=monitor_id,
        day=_window(incidents, now - DAY, now),
        week=_window(incidents, now - WEEK, now),
    )


def status_report(storage: Storage, *, now: datetime) -> StatusReport:
    monitors: list[Monitor] = storage.list_monitors()
    lines: list[StatusLine] = []
    tally: dict[Status, int] = {Status.UP: 0, Status.DOWN: 0, Status.UNKNOWN: 0}
    open_incidents = 0
    for monitor in monitors:
        status = status_for(storage.get_latest_result(monitor.id))
        tally[status] += 1
        open_incident = storage.get_open_incident(monitor.id)
        if open_incident is not None:
            open_incidents += 1
        lines.append(
            StatusLine(
                monitor_id=monitor.id,
                name=monitor.name,
                status=status,
                owning_team=monitor.owning_team,
                open_since=open_incident.opened_at if open_incident else None,
            )
        )
    return StatusReport(
        generated_at=now,
        total=len(monitors),
        up=tally[Status.UP],
        down=tally[Status.DOWN],
        unknown=tally[Status.UNKNOWN],
        open_incidents=open_incidents,
        monitors=lines,
    )
