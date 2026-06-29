from __future__ import annotations

from pathlib import Path


class WinamaxFileWatcher:
    def __init__(self, watch_path: Path) -> None:
        self.watch_path = watch_path

    def start(self) -> None:
        raise NotImplementedError("File watching is implemented in a later step.")