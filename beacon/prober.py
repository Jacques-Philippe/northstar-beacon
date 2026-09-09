"""Probing a monitored endpoint to produce an ``Outcome``.

The checker depends on the ``Prober`` protocol, not on httpx directly, so tests can
substitute a fake without any network access (same idea as the storage seam).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

import httpx

from beacon.models import Monitor, Outcome


class Prober(Protocol):
    async def probe(self, monitor: Monitor) -> Outcome: ...


class HttpxProber:
    """The real prober. Makes one HTTP request per probe and times it."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(follow_redirects=False)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def probe(self, monitor: Monitor) -> Outcome:
        started = time.perf_counter()
        try:
            response = await self._client.request(
                monitor.method,
                monitor.url,
                timeout=monitor.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            return Outcome(
                checked_at=datetime.now(UTC),
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
                response_ms=round((time.perf_counter() - started) * 1000, 1),
            )
        return Outcome(
            checked_at=datetime.now(UTC),
            ok=response.status_code == monitor.expected_status,
            status_code=response.status_code,
            response_ms=round((time.perf_counter() - started) * 1000, 1),
        )
