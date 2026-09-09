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

    # How often the checker wakes to look for monitors whose next check is due.
    checker_tick_seconds: float = 1.0

    # Whether the in-process checker runs at all. Tests set this false.
    checker_enabled: bool = True

    # Fallback timeout when a monitor does not specify one (it always does today).
    default_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
