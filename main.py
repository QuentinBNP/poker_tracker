from __future__ import annotations

from bootstrap import bootstrap_application, load_config
from ui import create_main_window


def main() -> None:
    config = load_config()
    database = bootstrap_application()
    root = create_main_window(database, config["player_name"])
    root.mainloop()


if __name__ == "__main__":
    main()