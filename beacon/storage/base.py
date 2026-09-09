"""The storage seam (ADR-0008).

Beat 1.1 ships only ``InMemoryStorage``. Beat 2.3 adds ``PostgresStorage`` and switches the
wiring. The protocol is kept deliberately narrow — exactly what the app uses today.
"""

from __future__ import annotations

from typing import Protocol

from beacon.models import Monitor, Outcome


class NotFound(Exception):
    """Raised when a monitor id does not exist."""


class Storage(Protocol):
    def create_monitor(self, monitor: Monitor) -> Monitor: ...

    def list_monitors(self) -> list[Monitor]: ...

    def get_monitor(self, monitor_id: str) -> Monitor: ...

    def update_monitor(self, monitor: Monitor) -> Monitor: ...

    def delete_monitor(self, monitor_id: str) -> None: ...

    def set_latest_result(self, monitor_id: str, outcome: Outcome) -> None: ...

    def get_latest_result(self, monitor_id: str) -> Outcome | None: ...
