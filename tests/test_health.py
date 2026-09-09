from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    assert client.get("/health/live").status_code == 200


def test_readiness(client: TestClient) -> None:
    assert client.get("/health/ready").status_code == 200
