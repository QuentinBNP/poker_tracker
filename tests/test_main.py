from __future__ import annotations

from typing import Any

import main as app_main


class _FakeRoot:
    def __init__(self) -> None:
        self.mainloop_called = False

    def mainloop(self) -> None:
        self.mainloop_called = True


def test_main_bootstraps_and_starts_ui(monkeypatch: Any) -> None:
    fake_root = _FakeRoot()
    fake_database = object()
    captured_hero_names: list[str] = []

    monkeypatch.setattr(app_main, "load_config", lambda: {"player_name": "MyPseudo"})
    monkeypatch.setattr(app_main, "bootstrap_application", lambda: fake_database)

    def fake_create_main_window(database: object, hero_name: str) -> _FakeRoot:
        assert database is fake_database
        captured_hero_names.append(hero_name)
        return fake_root

    monkeypatch.setattr(app_main, "create_main_window", fake_create_main_window)

    app_main.main()

    assert captured_hero_names == ["MyPseudo"]
    assert fake_root.mainloop_called is True