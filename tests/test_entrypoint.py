"""The container entrypoint dispatch (`python -m beacon <api|checker>`)."""

from __future__ import annotations

import pytest

import beacon.__main__ as entry


def test_api_entrypoint_binds_all_interfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(app: object, **kwargs: object) -> None:
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr("uvicorn.run", fake_run)

    entry.main(["api"])

    assert captured["app"] == "beacon.api.app:app"
    # 0.0.0.0, not 127.0.0.1 — the port has to be reachable from outside the container.
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8000


def test_checker_entrypoint_runs_the_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    ran = False

    async def fake_run(self: object) -> None:
        nonlocal ran
        ran = True

    monkeypatch.setattr("beacon.checker.Checker.run", fake_run)

    entry.main(["checker"])

    assert ran


def test_unknown_command_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    with pytest.raises(SystemExit):
        entry.main(["nope"])
