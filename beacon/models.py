"""Domain models.

These are Beacon's internal representation of the world, independent of the HTTP API
(whose request/response schemas live in ``beacon.api.schemas``) and of storage.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
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
    """The result of one probe of a monitor.

    In Beat 1.1 only the *latest* outcome per monitor is retained. Beat 2.1 promotes this
    into the append-only ``CheckResult`` entity.
    """

    checked_at: datetime = Field(default_factory=_now)
    ok: bool
    status_code: int | None = None
    response_ms: float | None = None
    error: str | None = None


def status_for(outcome: Outcome | None) -> Status:
    if outcome is None:
        return Status.UNKNOWN
    return Status.UP if outcome.ok else Status.DOWN
