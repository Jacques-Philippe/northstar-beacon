"""HTTP request/response schemas.

Kept separate from the domain model (``beacon.models``): the wire contract and the internal
representation are allowed to drift, and PATCH needs an all-optional shape the domain model
should not have.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from beacon.models import Incident, Monitor, Outcome, Status, status_for

Method = Literal["GET", "HEAD", "POST"]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Url = Annotated[str, Field(pattern=r"^https?://")]
ExpectedStatus = Annotated[int, Field(ge=100, le=599)]
Positive = Annotated[int, Field(gt=0)]
OwningTeam = Annotated[str, Field(min_length=1, max_length=200)]


def _check_timeout_below_interval(interval: int, timeout: int) -> None:
    if timeout >= interval:
        raise ValueError("timeout_seconds must be less than interval_seconds")


class MonitorCreate(BaseModel):
    name: Name
    url: Url
    method: Method = "GET"
    expected_status: ExpectedStatus = 200
    interval_seconds: Positive = 60
    timeout_seconds: Positive = 10
    enabled: bool = True
    owning_team: OwningTeam | None = None

    @model_validator(mode="after")
    def _validate(self) -> MonitorCreate:
        _check_timeout_below_interval(self.interval_seconds, self.timeout_seconds)
        return self

    def to_monitor(self) -> Monitor:
        return Monitor(**self.model_dump())


class MonitorUpdate(BaseModel):
    name: Name | None = None
    url: Url | None = None
    method: Method | None = None
    expected_status: ExpectedStatus | None = None
    interval_seconds: Positive | None = None
    timeout_seconds: Positive | None = None
    enabled: bool | None = None
    owning_team: OwningTeam | None = None

    def apply(self, monitor: Monitor) -> Monitor:
        updated = monitor.model_copy(update=self.model_dump(exclude_unset=True, exclude_none=True))
        _check_timeout_below_interval(updated.interval_seconds, updated.timeout_seconds)
        return updated


class MonitorRead(BaseModel):
    id: str
    name: str
    url: str
    method: str
    expected_status: int
    interval_seconds: int
    timeout_seconds: int
    enabled: bool
    owning_team: str | None
    created_at: datetime
    status: Status
    latest_result: Outcome | None

    @classmethod
    def build(cls, monitor: Monitor, latest: Outcome | None) -> MonitorRead:
        return cls(
            **monitor.model_dump(),
            status=status_for(latest),
            latest_result=latest,
        )


class IncidentRead(BaseModel):
    id: str
    monitor_id: str
    opened_at: datetime
    resolved_at: datetime | None
    duration_seconds: float
    ongoing: bool

    @classmethod
    def build(cls, incident: Incident, *, now: datetime) -> IncidentRead:
        return cls(
            id=incident.id,
            monitor_id=incident.monitor_id,
            opened_at=incident.opened_at,
            resolved_at=incident.resolved_at,
            duration_seconds=round(
                ((incident.resolved_at or now) - incident.opened_at).total_seconds(), 3
            ),
            ongoing=incident.is_open,
        )
