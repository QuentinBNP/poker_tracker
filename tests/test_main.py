from __future__ import annotations

from pathlib import Path
from typing import Any

import main as app_main
from database.importer import ImportReport
from watcher.file_watcher import DetectedFile


class _FakeRoot:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, Any]] = []
        self.destroy_called = False
        self.mainloop_called = False
        self.protocol_calls: list[tuple[str, Any]] = []

    def mainloop(self) -> None:
        self.mainloop_called = True

    def after(self, delay_ms: int, callback: Any) -> None:
        self.after_calls.append((delay_ms, callback))

    def destroy(self) -> None:
        self.destroy_called = True

    def protocol(self, name: str, callback: Any) -> None:
        self.protocol_calls.append((name, callback))


class _FakeDashboard:
    def __init__(self) -> None:
        self.refresh_called = False

    def refresh(self) -> None:
        self.refresh_called = True


class _FakeImporter:
    def __init__(self, database: object) -> None:
        self.database = database
        self.calls: list[tuple[Path, str]] = []

    def import_file(self, path: Path, file_type: str | None = None) -> ImportReport:
        self.calls.append((path, file_type or "hand_history"))
        return ImportReport(path=path, file_type=file_type or "hand_history", status="success")


class _FakeWatcher:
    def __init__(self, watch_path: Path, on_detected: Any) -> None:
        self.watch_path = watch_path
        self.on_detected = on_detected
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def process_existing_files(self) -> list[DetectedFile]:
        detected_file = DetectedFile(
            path=self.watch_path / "existing-summary.txt",
            file_type="tournament_summary",
        )
        self.on_detected(detected_file)
        return [detected_file]

    def stop(self) -> None:
        self.stopped = True


def test_main_bootstraps_and_starts_ui(monkeypatch: Any) -> None:
    fake_root = _FakeRoot()
    fake_dashboard = _FakeDashboard()
    fake_database = object()
    fake_importer = _FakeImporter(fake_database)
    fake_watch_path = Path("/tmp/winamax")
    fake_watcher: _FakeWatcher | None = None
    captured_configs: list[dict[str, object]] = []

    monkeypatch.setattr(
        app_main,
        "load_config",
        lambda: {
            "player_name": "MyPseudo",
            "winamax_folder": "data/winamax",
        },
    )
    monkeypatch.setattr(app_main, "bootstrap_application", lambda: fake_database)
    monkeypatch.setattr(app_main, "resolve_config_path", lambda config_path, path: fake_watch_path)
    monkeypatch.setattr(app_main, "DatabaseImporter", lambda database: fake_importer)

    def fake_watcher_factory(watch_path: Path, on_detected: Any) -> _FakeWatcher:
        nonlocal fake_watcher
        fake_watcher = _FakeWatcher(watch_path, on_detected)
        return fake_watcher

    monkeypatch.setattr(app_main, "WinamaxFileWatcher", fake_watcher_factory)

    def fake_create_main_window_with_view(
        database: object,
        config: dict[str, object],
        on_settings_saved: Any,
    ) -> tuple[_FakeRoot, _FakeDashboard]:
        assert database is fake_database
        assert callable(on_settings_saved)
        captured_configs.append(config)
        return fake_root, fake_dashboard

    monkeypatch.setattr(
        app_main,
        "create_main_window_with_view",
        fake_create_main_window_with_view,
    )

    app_main.main()

    assert captured_configs == [
        {
            "player_name": "MyPseudo",
            "winamax_folder": "data/winamax",
        }
    ]
    assert fake_root.mainloop_called is True
    assert fake_root.protocol_calls[0][0] == "WM_DELETE_WINDOW"
    assert fake_watcher is not None
    assert fake_watcher.watch_path == fake_watch_path
    assert fake_watcher.started is True
    assert fake_importer.calls == [
        (fake_watch_path / "existing-summary.txt", "tournament_summary")
    ]

    fake_watcher.on_detected(
        DetectedFile(
            path=Path("/tmp/hand.txt"),
            file_type="hand_history",
        )
    )

    assert fake_importer.calls == [
        (fake_watch_path / "existing-summary.txt", "tournament_summary"),
        (Path("/tmp/hand.txt"), "hand_history"),
    ]
    assert fake_root.after_calls == [(0, fake_dashboard.refresh), (0, fake_dashboard.refresh)]

    _, on_close = fake_root.protocol_calls[0]
    on_close()

    assert fake_watcher.stopped is True
    assert fake_root.destroy_called is True