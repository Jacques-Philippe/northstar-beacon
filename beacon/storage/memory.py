"""In-memory storage. Everything lives in a dict and dies with the process.

That it does not survive a restart is not a bug to be fixed here — it is the forcing
function for PostgreSQL in Act 2.
"""

from __future__ import annotations

from beacon.models import Monitor, Outcome
from beacon.storage.base import NotFound


class InMemoryStorage:
    def __init__(self) -> None:
        self._monitors: dict[str, Monitor] = {}
        self._latest: dict[str, Outcome] = {}

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
        self._latest.pop(monitor_id, None)

    def set_latest_result(self, monitor_id: str, outcome: Outcome) -> None:
        self._latest[monitor_id] = outcome

    def get_latest_result(self, monitor_id: str) -> Outcome | None:
        return self._latest.get(monitor_id)
