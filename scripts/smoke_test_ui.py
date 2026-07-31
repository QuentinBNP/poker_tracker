from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from bootstrap import bootstrap_application, load_config
    from ui import create_main_window

    config = load_config()
    database = bootstrap_application()
    root = create_main_window(database, config["player_name"])
    root.update_idletasks()
    root.update()
    root.destroy()
    print("Tk app initialized successfully")


if __name__ == "__main__":
    main()