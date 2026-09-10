"""The storage seam (ADR-0008).

Beat 1.1 ships only ``InMemoryStorage``. Beat 2.3 adds ``PostgresStorage`` and switches the
wiring. The protocol is kept deliberately narrow — exactly what the app uses today.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from beacon.models import CheckResult, Incident, Monitor, Outcome


class NotFound(Exception):
    """Raised when a monitor id does not exist."""


class Storage(Protocol):
    def create_monitor(self, monitor: Monitor) -> Monitor: ...

    def list_monitors(self) -> list[Monitor]: ...

    def get_monitor(self, monitor_id: str) -> Monitor: ...

    def update_monitor(self, monitor: Monitor) -> Monitor: ...

    def delete_monitor(self, monitor_id: str) -> None: ...

    # --- check results (append-only) ---

    def append_result(self, result: CheckResult) -> None: ...

    def get_latest_result(self, monitor_id: str) -> Outcome | None: ...

    def list_results(self, monitor_id: str, *, since: datetime | None = None) -> list[CheckResult]:
        """Ascending by ``checked_at``. ``since`` is inclusive when given."""
        ...

    # --- incidents (derived from the result stream by the checker) ---

    def add_incident(self, incident: Incident) -> Incident: ...

    def resolve_incident(self, incident_id: str, resolved_at: datetime) -> None: ...

    def get_open_incident(self, monitor_id: str) -> Incident | None: ...

    def list_incidents(
        self, *, monitor_id: str | None = None, since: datetime | None = None
    ) -> list[Incident]:
        """Newest first (by ``opened_at``). ``since`` keeps incidents that were still open
        at or after that instant."""
        ...
