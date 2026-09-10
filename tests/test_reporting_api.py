"""The /uptime, /incidents and /status endpoints (Beat 2.1)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from beacon.models import CheckResult, Incident
from beacon.storage import InMemoryStorage

VALID = {
    "name": "api",
    "url": "https://api.example/health",
    "interval_seconds": 60,
    "timeout_seconds": 10,
}


def test_uptime_404_for_unknown_monitor(client: TestClient) -> None:
    assert client.get("/monitors/nope/uptime").status_code == 404


def test_uptime_reports_day_and_week(client: TestClient, storage: InMemoryStorage) -> None:
    monitor_id = client.post("/monitors", json=VALID).json()["id"]
    now = datetime.now(UTC)
    storage.add_incident(
        Incident(
            monitor_id=monitor_id,
            opened_at=now - timedelta(hours=2),
            resolved_at=now - timedelta(hours=1),
        )
    )
    body = client.get(f"/monitors/{monitor_id}/uptime").json()
    assert body["day"]["downtime_seconds"] == 3600.0
    assert body["day"]["uptime_percent"] == round((86400 - 3600) / 86400 * 100, 4)
    # one bad hour is a smaller share of a week than of a day, so week uptime is higher
    assert body["week"]["uptime_percent"] > body["day"]["uptime_percent"]


def test_incidents_list_filters_by_monitor(client: TestClient, storage: InMemoryStorage) -> None:
    a = client.post("/monitors", json=VALID).json()["id"]
    b = client.post("/monitors", json={**VALID, "url": "https://b.example"}).json()["id"]
    now = datetime.now(UTC)
    storage.add_incident(Incident(monitor_id=a, opened_at=now - timedelta(minutes=10)))
    storage.add_incident(
        Incident(
            monitor_id=b,
            opened_at=now - timedelta(hours=1),
            resolved_at=now - timedelta(minutes=30),
        )
    )

    all_incidents = client.get("/incidents").json()
    assert len(all_incidents) == 2

    just_a = client.get("/incidents", params={"monitor_id": a}).json()
    assert len(just_a) == 1
    assert just_a[0]["monitor_id"] == a
    assert just_a[0]["ongoing"] is True
    assert just_a[0]["resolved_at"] is None


def test_status_aggregates_all_monitors(client: TestClient, storage: InMemoryStorage) -> None:
    up = client.post("/monitors", json=VALID).json()["id"]
    client.post("/monitors", json={**VALID, "url": "https://down.example"}).json()
    storage.append_result(CheckResult(monitor_id=up, ok=True, checked_at=datetime.now(UTC)))

    body = client.get("/status").json()
    assert body["total"] == 2
    assert body["up"] == 1
    assert body["unknown"] == 1
    assert len(body["monitors"]) == 2
