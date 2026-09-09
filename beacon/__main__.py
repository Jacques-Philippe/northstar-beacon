"""Container entrypoint: ``python -m beacon <api|checker>``.

One image, two entrypoints (Beat 1.2). The container command selects which process the
container runs:

- ``api``     — serves the HTTP API, and for now also runs the checker in-process (the
                checker splits into its own Deployment in Beat 3.3).
- ``checker`` — runs the probe loop on its own. The command exists so the image is ready
                for that split; today it runs against in-memory storage and has nothing to
                probe until PostgreSQL arrives in Beat 2.3.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from beacon import logging as beacon_logging
from beacon.config import get_settings

log = logging.getLogger("beacon")


def _run_api() -> None:
    import uvicorn

    settings = get_settings()
    log.info("api entrypoint starting", extra={"host": settings.host, "port": settings.port})
    # log_config=None: don't let uvicorn install its own handlers — Beacon's JSON logging
    # (configured below and again in create_app) owns the root logger.
    uvicorn.run(
        "beacon.api.app:app",
        host=settings.host,
        port=settings.port,
        log_config=None,
    )


async def _run_checker_async() -> None:
    from beacon.checker import Checker
    from beacon.prober import HttpxProber
    from beacon.storage import InMemoryStorage

    settings = get_settings()
    prober = HttpxProber()
    checker = Checker(InMemoryStorage(), prober, settings.checker_tick_seconds)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, checker.stop)

    log.info("checker entrypoint starting", extra={"storage": "in-memory"})
    try:
        await checker.run()
    finally:
        await prober.aclose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="beacon", description=__doc__)
    parser.add_argument("command", choices=("api", "checker"))
    args = parser.parse_args(argv)

    beacon_logging.configure(get_settings().log_level)

    if args.command == "api":
        _run_api()
    else:
        asyncio.run(_run_checker_async())


if __name__ == "__main__":
    main()
