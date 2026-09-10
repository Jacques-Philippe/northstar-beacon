"""Domain models.

These are Beacon's internal representation of the world, independent of the HTTP API
(whose request/response schemas live in ``beacon.api.schemas``) and of storage.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Status(enum.StrEnum):
    """A monitor's current status, derived from its latest check outcome."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"  # no probe has completed yet


class Monitor(BaseModel):
    """The configured intent to watch one HTTP endpoint on a schedule."""

    id: str = Field(default_factory=_new_id)
    name: str
    url: str
    method: str = "GET"
    expected_status: int = 200
    interval_seconds: int = 60
    timeout_seconds: int = 10
    enabled: bool = True
    owning_team: str | None = None  # the team to ping when this monitor is failing
    created_at: datetime = Field(default_factory=_now)


class Outcome(BaseModel):
    """The result of one probe of a monitor — the value the prober returns.

    It is the transient shape; :class:`CheckResult` is the same information once it has been
    written to storage against a monitor.
    """

    checked_at: datetime = Field(default_factory=_now)
    ok: bool
    status_code: int | None = None
    response_ms: float | None = None
    error: str | None = None


class CheckResult(BaseModel):
    """The recorded outcome of one probe of a monitor. Append-only: never updated, never
    deleted while the monitor exists. Uptime detail and the incident state machine are both
    derived from the ``CheckResult`` stream."""

    id: str = Field(default_factory=_new_id)
    monitor_id: str
    checked_at: datetime = Field(default_factory=_now)
    ok: bool
    status_code: int | None = None
    response_ms: float | None = None
    error: str | None = None

    @classmethod
    def of(cls, monitor_id: str, outcome: Outcome) -> CheckResult:
        return cls(monitor_id=monitor_id, **outcome.model_dump())

    def as_outcome(self) -> Outcome:
        return Outcome(**{k: getattr(self, k) for k in Outcome.model_fields})


class Incident(BaseModel):
    """A period during which a monitor is failing. Opens once a run of consecutive failed
    ``CheckResult``s reaches the configured threshold — backdated to the *first* failure in
    that run — and closes on the first success (``resolved_at``)."""

    id: str = Field(default_factory=_new_id)
    monitor_id: str
    opened_at: datetime
    resolved_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    def downtime_within(self, since: datetime, until: datetime) -> timedelta:
        """How much of this incident falls inside ``[since, until]``. An open incident is
        treated as running up to ``until``."""
        start = max(self.opened_at, since)
        end = min(self.resolved_at or until, until)
        return max(end - start, timedelta(0))


def status_for(outcome: Outcome | None) -> Status:
    if outcome is None:
        return Status.UNKNOWN
    return Status.UP if outcome.ok else Status.DOWN
