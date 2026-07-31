from __future__ import annotations

from bootstrap import (
    bootstrap_application,
    get_default_config_path,
    load_config,
    resolve_config_path,
)
from database.importer import DatabaseImporter
from logging_system import get_logger
from ui import create_main_window_with_view
from watcher.file_watcher import DetectedFile, WinamaxFileWatcher


def main() -> None:
    config = load_config()
    database = bootstrap_application()
    importer = DatabaseImporter(database)
    watch_path = resolve_config_path(get_default_config_path(), config["winamax_folder"])
    logger = get_logger("watcher")

    root, dashboard = create_main_window_with_view(database, config["player_name"])

    def on_detected(detected: DetectedFile) -> None:
        report = importer.import_file(detected.path, detected.file_type)
        if report.status == "success":
            root.after(0, dashboard.refresh)

    watcher = WinamaxFileWatcher(watch_path, on_detected=on_detected)

    try:
        watcher.start()
    except FileNotFoundError:
        logger.warning("Watch path does not exist: %s", watch_path)

    def on_close() -> None:
        watcher.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()