from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status

from beacon.api.schemas import IncidentRead, MonitorCreate, MonitorRead, MonitorUpdate
from beacon.reporting import MonitorUptime, StatusReport, monitor_uptime, status_report
from beacon.storage.base import NotFound, Storage

log = logging.getLogger("beacon.api")

router = APIRouter()


def _storage(request: Request) -> Storage:
    return request.app.state.storage


def _now() -> datetime:
    return datetime.now(UTC)


def _read(storage: Storage, monitor_id: str) -> MonitorRead:
    try:
        monitor = storage.get_monitor(monitor_id)
    except NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found") from None
    return MonitorRead.build(monitor, storage.get_latest_result(monitor_id))


@router.get("/monitors", response_model=list[MonitorRead])
def list_monitors(request: Request) -> list[MonitorRead]:
    storage = _storage(request)
    return [MonitorRead.build(m, storage.get_latest_result(m.id)) for m in storage.list_monitors()]


@router.post("/monitors", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
def create_monitor(request: Request, body: MonitorCreate) -> MonitorRead:
    storage = _storage(request)
    monitor = storage.create_monitor(body.to_monitor())
    log.info("monitor created", extra={"monitor_id": monitor.id, "url": monitor.url})
    return MonitorRead.build(monitor, None)


@router.get("/monitors/{monitor_id}", response_model=MonitorRead)
def get_monitor(request: Request, monitor_id: str) -> MonitorRead:
    return _read(_storage(request), monitor_id)


@router.patch("/monitors/{monitor_id}", response_model=MonitorRead)
def update_monitor(request: Request, monitor_id: str, body: MonitorUpdate) -> MonitorRead:
    storage = _storage(request)
    try:
        current = storage.get_monitor(monitor_id)
    except NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found") from None
    try:
        updated = body.apply(current)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    storage.update_monitor(updated)
    log.info("monitor updated", extra={"monitor_id": monitor_id})
    return _read(storage, monitor_id)


@router.delete("/monitors/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(request: Request, monitor_id: str) -> Response:
    storage = _storage(request)
    try:
        storage.delete_monitor(monitor_id)
    except NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found") from None
    log.info("monitor deleted", extra={"monitor_id": monitor_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/monitors/{monitor_id}/uptime", response_model=MonitorUptime)
def get_monitor_uptime(request: Request, monitor_id: str) -> MonitorUptime:
    storage = _storage(request)
    try:
        storage.get_monitor(monitor_id)
    except NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found") from None
    return monitor_uptime(storage, monitor_id, now=_now())


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(request: Request, monitor_id: str | None = None) -> list[IncidentRead]:
    storage = _storage(request)
    now = _now()
    incidents = storage.list_incidents(monitor_id=monitor_id)
    return [IncidentRead.build(i, now=now) for i in incidents]


@router.get("/status", response_model=StatusReport)
def get_status(request: Request) -> StatusReport:
    return status_report(_storage(request), now=_now())


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready() -> dict[str, str]:
    # Beat 1.1: a stub. Beat 3.1 makes this check the database connection.
    return {"status": "ok"}
