"""Application configuration, read from the environment.

This is the seam that Beat 2.4 wires a Kubernetes ConfigMap/Secret into. For now it is
just process environment variables, prefixed ``BEACON_``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BEACON_")

    log_level: str = "INFO"

    # Where the api entrypoint binds. 0.0.0.0 so the port is reachable from outside the
    # container (a 127.0.0.1 bind is the classic "works on my laptop, dead in Docker" bug).
    host: str = "0.0.0.0"
    port: int = 8000

    # How often the checker wakes to look for monitors whose next check is due.
    checker_tick_seconds: float = 1.0

    # Whether the in-process checker runs at all. Tests set this false.
    checker_enabled: bool = True

    # Fallback timeout when a monitor does not specify one (it always does today).
    default_timeout_seconds: float = 10.0

    # Consecutive failed checks before an incident opens. Recovery is asymmetric: a single
    # success closes the incident. Michael is expected to renegotiate this ("what counts as
    # degraded"), hence a config knob rather than a literal.
    incident_failure_threshold: int = 3

    # Beat 2.2: the frontend is reached via its own port-forward, a different origin from
    # `api`'s, so the browser needs CORS headers to allow it. This exists only to prop up
    # the two-port-forward workaround — Beat 2.3 collapses both to one origin behind an
    # Ingress and removes it.
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
