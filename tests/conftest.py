from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from beacon.api.app import create_app
from beacon.config import Settings
from beacon.models import Monitor, Outcome
from beacon.storage import InMemoryStorage


class FakeProber:
    """Records what it was asked to probe and returns a canned outcome.

    Default: every probe succeeds with 200. Override per-url via ``set``.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._outcomes: dict[str, Outcome] = {}

    def set(self, url: str, outcome: Outcome) -> None:
        self._outcomes[url] = outcome

    async def probe(self, monitor: Monitor) -> Outcome:
        self.calls.append(monitor.url)
        return self._outcomes.get(monitor.url, Outcome(ok=True, status_code=200, response_ms=1.0))


@pytest.fixture
def storage() -> InMemoryStorage:
    return InMemoryStorage()


@pytest.fixture
def prober() -> FakeProber:
    return FakeProber()


@pytest.fixture
def client(storage: InMemoryStorage, prober: FakeProber) -> TestClient:
    app = create_app(
        settings=Settings(checker_enabled=False),
        storage=storage,
        prober=prober,
    )
    with TestClient(app) as test_client:
        yield test_client
