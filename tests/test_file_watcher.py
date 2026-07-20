from __future__ import annotations

from pathlib import Path

from watcher.file_watcher import DetectedFile, WinamaxFileWatcher


def test_process_existing_files_classifies_summary_and_hand_history(tmp_path: Path) -> None:
    detected: list[DetectedFile] = []
    watcher = WinamaxFileWatcher(tmp_path, on_detected=detected.append)

    hand_history = tmp_path / "20260628_Freeroll(1119027769)_real_holdem_no-limit.txt"
    summary = tmp_path / "20260628_Freeroll(1119027769)_real_holdem_no-limit_summary.txt"
    hand_history.write_text("hand", encoding="utf-8")
    summary.write_text("summary", encoding="utf-8")

    processed = watcher.process_existing_files()

    assert processed == [
        DetectedFile(path=hand_history, file_type="hand_history"),
        DetectedFile(path=summary, file_type="tournament_summary"),
    ]
    assert detected == processed


def test_handle_event_path_ignores_duplicate_unchanged_file(tmp_path: Path) -> None:
    detected: list[DetectedFile] = []
    watcher = WinamaxFileWatcher(tmp_path, on_detected=detected.append)
    hand_history = tmp_path / "20260628_Nice 23_real_holdem_no-limit.txt"
    hand_history.write_text("first version", encoding="utf-8")

    first_detection = watcher.handle_event_path(hand_history)
    second_detection = watcher.handle_event_path(hand_history)

    assert first_detection == DetectedFile(path=hand_history, file_type="hand_history")
    assert second_detection is None
    assert detected == [DetectedFile(path=hand_history, file_type="hand_history")]


def test_handle_event_path_reprocesses_file_after_change(tmp_path: Path) -> None:
    detected: list[DetectedFile] = []
    watcher = WinamaxFileWatcher(tmp_path, on_detected=detected.append)
    hand_history = tmp_path / "20260628_Kill The Fish(1119034571)_real_holdem_no-limit.txt"
    hand_history.write_text("v1", encoding="utf-8")

    watcher.handle_event_path(hand_history)
    hand_history.write_text("v2 changed", encoding="utf-8")

    second_detection = watcher.handle_event_path(hand_history)

    assert second_detection == DetectedFile(path=hand_history, file_type="hand_history")
    assert detected == [
        DetectedFile(path=hand_history, file_type="hand_history"),
        DetectedFile(path=hand_history, file_type="hand_history"),
    ]


def test_start_raises_for_missing_watch_path(tmp_path: Path) -> None:
    watcher = WinamaxFileWatcher(tmp_path / "missing")

    try:
        watcher.start()
    except FileNotFoundError as error:
        assert "Watch path does not exist" in str(error)
    else:
        raise AssertionError("Expected start() to fail for a missing path")