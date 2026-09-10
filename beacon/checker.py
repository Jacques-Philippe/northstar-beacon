"""The checker: probes monitors when their next check is due.

In Beat 1.1 it runs as a background asyncio task inside the api process (started from the
FastAPI lifespan). It splits into its own Deployment in Beat 3.3.

``tick`` does one full pass and is what tests drive with a controlled ``now``. ``run`` is
just ``tick`` on a timer.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from beacon.models import CheckResult, Incident, Monitor, Outcome
from beacon.prober import Prober
from beacon.storage.base import Storage

log = logging.getLogger("beacon.checker")


class Checker:
    def __init__(
        self,
        storage: Storage,
        prober: Prober,
        tick_seconds: float = 1.0,
        *,
        incident_failure_threshold: int = 3,
    ) -> None:
        self._storage = storage
        self._prober = prober
        self._tick_seconds = tick_seconds
        self._failure_threshold = incident_failure_threshold
        self._stopped = asyncio.Event()

    def _is_due(self, monitor: Monitor, now: datetime) -> bool:
        if not monitor.enabled:
            return False
        latest = self._storage.get_latest_result(monitor.id)
        if latest is None:
            return True
        elapsed = (now - latest.checked_at).total_seconds()
        return elapsed >= monitor.interval_seconds

    async def tick(self, now: datetime) -> None:
        for monitor in self._storage.list_monitors():
            if not self._is_due(monitor, now):
                continue
            outcome = await self._prober.probe(monitor)
            self._storage.append_result(CheckResult.of(monitor.id, outcome))
            self._reconcile_incident(monitor, outcome)
            log.info(
                "probe",
                extra={
                    "monitor_id": monitor.id,
                    "url": monitor.url,
                    "ok": outcome.ok,
                    "status_code": outcome.status_code,
                    "response_ms": outcome.response_ms,
                    "error": outcome.error,
                },
            )

    def _reconcile_incident(self, monitor: Monitor, outcome: Outcome) -> None:
        """Open or close this monitor's incident based on the check just recorded.

        Open: once the trailing run of consecutive failures reaches the threshold, backdated
        to the first failure in that run. Close: on the first success.
        """
        open_incident = self._storage.get_open_incident(monitor.id)
        if outcome.ok:
            if open_incident is not None:
                self._storage.resolve_incident(open_incident.id, outcome.checked_at)
                log.info(
                    "incident resolved",
                    extra={"monitor_id": monitor.id, "incident_id": open_incident.id},
                )
            return
        if open_incident is not None:
            return
        run = self._trailing_failure_run(monitor.id)
        if len(run) >= self._failure_threshold:
            incident = self._storage.add_incident(
                Incident(monitor_id=monitor.id, opened_at=run[0].checked_at)
            )
            log.info(
                "incident opened",
                extra={
                    "monitor_id": monitor.id,
                    "incident_id": incident.id,
                    "opened_at": incident.opened_at.isoformat(),
                    "consecutive_failures": len(run),
                },
            )

    def _trailing_failure_run(self, monitor_id: str) -> list[CheckResult]:
        """The unbroken run of failures ending with the most recent result, oldest first."""
        run: list[CheckResult] = []
        for result in reversed(self._storage.list_results(monitor_id)):
            if result.ok:
                break
            run.append(result)
        run.reverse()
        return run

    async def run(self) -> None:
        log.info("checker started", extra={"tick_seconds": self._tick_seconds})
        self._stopped.clear()
        try:
            while not self._stopped.is_set():
                try:
                    await self.tick(datetime.now(UTC))
                except Exception:  # noqa: BLE001 — a bad probe must not kill the loop
                    log.exception("checker tick failed")
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self._tick_seconds)
                except TimeoutError:
                    pass
        finally:
            log.info("checker stopped")

    def stop(self) -> None:
        self._stopped.set()
