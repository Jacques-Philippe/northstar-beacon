from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from beacon import logging as beacon_logging
from beacon.api.routes import router
from beacon.checker import Checker
from beacon.config import Settings, get_settings
from beacon.prober import HttpxProber, Prober
from beacon.storage import InMemoryStorage
from beacon.storage.base import Storage

log = logging.getLogger("beacon")


def create_app(
    *,
    settings: Settings | None = None,
    storage: Storage | None = None,
    prober: Prober | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    beacon_logging.configure(settings.log_level)
    storage = storage if storage is not None else InMemoryStorage()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        log.info("beacon starting", extra={"checker_enabled": settings.checker_enabled})
        owns_prober = prober is None
        active_prober = prober or HttpxProber()
        checker_task: asyncio.Task[None] | None = None
        checker: Checker | None = None
        if settings.checker_enabled:
            checker = Checker(storage, active_prober, settings.checker_tick_seconds)
            checker_task = asyncio.create_task(checker.run())
        try:
            yield
        finally:
            if checker and checker_task:
                checker.stop()
                await checker_task
            if owns_prober and isinstance(active_prober, HttpxProber):
                await active_prober.aclose()
            log.info("beacon stopped")

    app = FastAPI(title="Beacon", lifespan=lifespan)
    app.state.storage = storage
    app.include_router(router)
    return app


app = create_app()
