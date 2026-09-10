"""In-memory storage. Everything lives in a dict and dies with the process.

That it does not survive a restart is not a bug to be fixed here — it is the forcing
function for PostgreSQL in Act 2.
"""

from __future__ import annotations

from datetime import datetime

from beacon.models import CheckResult, Incident, Monitor, Outcome
from beacon.storage.base import NotFound


class InMemoryStorage:
    def __init__(self) -> None:
        self._monitors: dict[str, Monitor] = {}
        self._results: dict[str, list[CheckResult]] = {}
        self._incidents: dict[str, Incident] = {}

    def create_monitor(self, monitor: Monitor) -> Monitor:
        self._monitors[monitor.id] = monitor
        return monitor

    def list_monitors(self) -> list[Monitor]:
        return sorted(self._monitors.values(), key=lambda m: m.created_at)

    def get_monitor(self, monitor_id: str) -> Monitor:
        try:
            return self._monitors[monitor_id]
        except KeyError:
            raise NotFound(monitor_id) from None

    def update_monitor(self, monitor: Monitor) -> Monitor:
        if monitor.id not in self._monitors:
            raise NotFound(monitor.id)
        self._monitors[monitor.id] = monitor
        return monitor

    def delete_monitor(self, monitor_id: str) -> None:
        if self._monitors.pop(monitor_id, None) is None:
            raise NotFound(monitor_id)
        self._results.pop(monitor_id, None)
        self._incidents = {i.id: i for i in self._incidents.values() if i.monitor_id != monitor_id}

    # --- check results ---

    def append_result(self, result: CheckResult) -> None:
        self._results.setdefault(result.monitor_id, []).append(result)

    def get_latest_result(self, monitor_id: str) -> Outcome | None:
        results = self._results.get(monitor_id)
        if not results:
            return None
        return max(results, key=lambda r: r.checked_at).as_outcome()

    def list_results(self, monitor_id: str, *, since: datetime | None = None) -> list[CheckResult]:
        results = sorted(self._results.get(monitor_id, []), key=lambda r: r.checked_at)
        if since is not None:
            results = [r for r in results if r.checked_at >= since]
        return results

    # --- incidents ---

    def add_incident(self, incident: Incident) -> Incident:
        self._incidents[incident.id] = incident
        return incident

    def resolve_incident(self, incident_id: str, resolved_at: datetime) -> None:
        incident = self._incidents.get(incident_id)
        if incident is not None and incident.resolved_at is None:
            self._incidents[incident_id] = incident.model_copy(update={"resolved_at": resolved_at})

    def get_open_incident(self, monitor_id: str) -> Incident | None:
        for incident in self._incidents.values():
            if incident.monitor_id == monitor_id and incident.is_open:
                return incident
        return None

    def list_incidents(
        self, *, monitor_id: str | None = None, since: datetime | None = None
    ) -> list[Incident]:
        incidents = list(self._incidents.values())
        if monitor_id is not None:
            incidents = [i for i in incidents if i.monitor_id == monitor_id]
        if since is not None:
            incidents = [i for i in incidents if i.resolved_at is None or i.resolved_at >= since]
        return sorted(incidents, key=lambda i: i.opened_at, reverse=True)
