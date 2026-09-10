from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from beacon.models import CheckResult
from beacon.storage import InMemoryStorage

VALID = {
    "name": "Northstar API",
    "url": "https://api.northstar.example/health",
    "interval_seconds": 60,
    "timeout_seconds": 10,
}


def test_create_returns_201_with_defaults_and_unknown_status(client: TestClient) -> None:
    resp = client.post("/monitors", json=VALID)
    assert resp.status_code == 201
    body = resp.json()
    assert body["method"] == "GET"
    assert body["expected_status"] == 200
    assert body["enabled"] is True
    assert body["status"] == "unknown"
    assert body["latest_result"] is None
    assert body["id"]


def test_owning_team_defaults_to_null_and_round_trips(client: TestClient) -> None:
    assert client.post("/monitors", json=VALID).json()["owning_team"] is None

    created = client.post("/monitors", json={**VALID, "owning_team": "Platform"}).json()
    assert created["owning_team"] == "Platform"
    assert client.get(f"/monitors/{created['id']}").json()["owning_team"] == "Platform"


def test_owning_team_set_via_patch(client: TestClient) -> None:
    monitor_id = client.post("/monitors", json=VALID).json()["id"]
    resp = client.patch(f"/monitors/{monitor_id}", json={"owning_team": "Payments"})
    assert resp.status_code == 200
    assert resp.json()["owning_team"] == "Payments"


def test_rejects_empty_owning_team(client: TestClient) -> None:
    assert client.post("/monitors", json={**VALID, "owning_team": ""}).status_code == 422


def test_list_is_empty_then_reflects_creates(client: TestClient) -> None:
    assert client.get("/monitors").json() == []
    client.post("/monitors", json=VALID)
    assert len(client.get("/monitors").json()) == 1


def test_get_unknown_is_404(client: TestClient) -> None:
    assert client.get("/monitors/does-not-exist").status_code == 404


def test_patch_partial_update(client: TestClient) -> None:
    monitor_id = client.post("/monitors", json=VALID).json()["id"]
    resp = client.patch(f"/monitors/{monitor_id}", json={"enabled": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["name"] == VALID["name"]  # untouched


def test_patch_unknown_is_404(client: TestClient) -> None:
    assert client.patch("/monitors/nope", json={"enabled": False}).status_code == 404


def test_delete(client: TestClient) -> None:
    monitor_id = client.post("/monitors", json=VALID).json()["id"]
    assert client.delete(f"/monitors/{monitor_id}").status_code == 204
    assert client.get(f"/monitors/{monitor_id}").status_code == 404
    assert client.delete(f"/monitors/{monitor_id}").status_code == 404


def test_status_derived_from_latest_result(client: TestClient, storage: InMemoryStorage) -> None:
    monitor_id = client.post("/monitors", json=VALID).json()["id"]
    t0 = datetime.now(UTC)
    storage.append_result(
        CheckResult(monitor_id=monitor_id, ok=False, status_code=500, checked_at=t0)
    )
    assert client.get(f"/monitors/{monitor_id}").json()["status"] == "down"
    storage.append_result(
        CheckResult(
            monitor_id=monitor_id, ok=True, status_code=200, checked_at=t0 + timedelta(seconds=60)
        )
    )
    assert client.get(f"/monitors/{monitor_id}").json()["status"] == "up"


def test_rejects_bad_url(client: TestClient) -> None:
    resp = client.post("/monitors", json={**VALID, "url": "ftp://nope"})
    assert resp.status_code == 422


def test_rejects_bad_method(client: TestClient) -> None:
    resp = client.post("/monitors", json={**VALID, "method": "TRACE"})
    assert resp.status_code == 422


def test_rejects_non_positive_interval(client: TestClient) -> None:
    resp = client.post("/monitors", json={**VALID, "interval_seconds": 0})
    assert resp.status_code == 422


def test_rejects_timeout_not_below_interval_on_create(client: TestClient) -> None:
    resp = client.post("/monitors", json={**VALID, "interval_seconds": 10, "timeout_seconds": 10})
    assert resp.status_code == 422


def test_rejects_timeout_not_below_interval_on_patch(client: TestClient) -> None:
    monitor_id = client.post("/monitors", json=VALID).json()["id"]
    resp = client.patch(f"/monitors/{monitor_id}", json={"timeout_seconds": 60})
    assert resp.status_code == 422
