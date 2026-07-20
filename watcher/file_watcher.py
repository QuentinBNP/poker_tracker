from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
except ModuleNotFoundError:  # pragma: no cover - exercised when dependency is absent
    FileSystemEvent = object

    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass

    Observer = None  # type: ignore[assignment]


WatcherCallback = Callable[["DetectedFile"], None]


@dataclass(slots=True)
class DetectedFile:
    path: Path
    file_type: str


class WinamaxFileWatcher:
    def __init__(
        self,
        watch_path: Path,
        on_detected: WatcherCallback | None = None,
    ) -> None:
        self.watch_path = watch_path
        self.on_detected = on_detected or self._default_callback
        self._observer: Observer | None = None
        self._seen_signatures: dict[Path, tuple[int, int]] = {}

    def start(self) -> None:
        if not self.watch_path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {self.watch_path}")

        if Observer is None:
            raise RuntimeError(
                "watchdog is not installed. Install project dependencies before starting the watcher."
            )

        if self._observer is not None:
            return

        event_handler = _WinamaxEventHandler(self)
        observer = Observer()
        observer.schedule(event_handler, str(self.watch_path), recursive=False)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        if self._observer is None:
            return

        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None

    def process_existing_files(self) -> list[DetectedFile]:
        detections: list[DetectedFile] = []

        for path in sorted(self.watch_path.glob("*.txt")):
            detection = self._handle_path(path)
            if detection is not None:
                detections.append(detection)

        return detections

    def handle_event_path(self, path: Path) -> DetectedFile | None:
        return self._handle_path(path)

    def _handle_path(self, path: Path) -> DetectedFile | None:
        if not path.exists() or path.suffix.lower() != ".txt":
            return None

        signature = self._build_signature(path)
        if self._seen_signatures.get(path) == signature:
            return None

        self._seen_signatures[path] = signature
        detection = DetectedFile(path=path, file_type=self._classify_file(path))
        self.on_detected(detection)
        return detection

    @staticmethod
    def _build_signature(path: Path) -> tuple[int, int]:
        stats = path.stat()
        return (stats.st_mtime_ns, stats.st_size)

    @staticmethod
    def _classify_file(path: Path) -> str:
        if path.name.endswith("_summary.txt"):
            return "tournament_summary"

        return "hand_history"

    @staticmethod
    def _default_callback(detection: DetectedFile) -> None:
        label = "summary" if detection.file_type == "tournament_summary" else "hand history"
        print(f"New {label} detected: {detection.path.name}")


class _WinamaxEventHandler(FileSystemEventHandler):
    def __init__(self, watcher: WinamaxFileWatcher) -> None:
        self.watcher = watcher

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def _handle(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        self.watcher.handle_event_path(Path(event.src_path))