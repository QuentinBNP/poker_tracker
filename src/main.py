from __future__ import annotations

import logging
from pathlib import Path
from threading import Thread
from typing import Callable

from bootstrap import (
    bootstrap_application,
    get_default_config_path,
    load_config,
    resolve_config_path,
    save_config,
)
from database.importer import DatabaseImporter
from logging_system import get_logger
from ui import create_main_window_with_view
from watcher.file_watcher import DetectedFile, WinamaxFileWatcher


def main() -> None:
    config = load_config()
    database = bootstrap_application()
    importer = DatabaseImporter(database)
    logger = get_logger("watcher")
    watcher: WinamaxFileWatcher | None = None

    def import_detected(detected: DetectedFile) -> bool:
        report = importer.import_file(detected.path, detected.file_type)
        return report.status == "success"

    def on_detected(detected: DetectedFile) -> None:
        if import_detected(detected):
            root.after(0, dashboard.refresh)

    def start_watcher() -> None:
        nonlocal watcher
        if watcher is not None:
            watcher.stop()

        watch_path = resolve_config_path(get_default_config_path(), config["winamax_folder"])
        watcher = WinamaxFileWatcher(watch_path, on_detected=on_detected)
        try:
            watcher.start()
            Thread(
                target=_process_existing_files,
                args=(
                    watcher,
                    watch_path,
                    logger,
                    import_detected,
                    lambda imported: root.after(0, dashboard.refresh) if imported else None,
                ),
                daemon=True,
            ).start()
        except FileNotFoundError:
            logger.warning("Watch path does not exist: %s", watch_path)

    def on_settings_saved(updated_config: dict[str, str]) -> None:
        config.clear()
        config.update(updated_config)
        save_config(updated_config)
        start_watcher()

    root, dashboard = create_main_window_with_view(database, config, on_settings_saved)
    start_watcher()

    def on_close() -> None:
        if watcher is not None:
            watcher.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def _process_existing_files(
    watcher: WinamaxFileWatcher,
    watch_path: Path,
    logger: logging.Logger,
    import_detected: Callable[[DetectedFile], bool] | None = None,
    on_completed: Callable[[bool], None] | None = None,
) -> None:
    successfully_imported = False

    def process_detection(detected: DetectedFile) -> None:
        nonlocal successfully_imported
        if import_detected is None or import_detected(detected):
            successfully_imported = True

    imported_files = watcher.process_existing_files(process_detection)
    logger.info("Processed %d existing Winamax files from %s", len(imported_files), watch_path)
    if on_completed is not None:
        on_completed(successfully_imported)


if __name__ == "__main__":
    main()