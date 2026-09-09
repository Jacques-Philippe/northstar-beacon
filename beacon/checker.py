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

from beacon.models import Monitor
from beacon.prober import Prober
from beacon.storage.base import Storage

log = logging.getLogger("beacon.checker")


class Checker:
    def __init__(self, storage: Storage, prober: Prober, tick_seconds: float = 1.0) -> None:
        self._storage = storage
        self._prober = prober
        self._tick_seconds = tick_seconds
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
            self._storage.set_latest_result(monitor.id, outcome)
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
