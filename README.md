# Poker Tracker

Poker Tracker is a personal Winamax desktop tracker written in Python.

The current codebase can:

- parse Winamax tournament summary files
- parse Winamax hand history files for tournaments and cash games
- store tournaments, hands, players, actions, and import history in SQLite
- import parsed files into the database
- monitor a folder for new or modified `.txt` files
- open a Tkinter desktop interface showing a dashboard, recent hands, recent tournaments, and basic poker statistics
- write application, parser, database, watcher, and import logs

## Current Status

This project is functional as a local MVP foundation, but it is not fully automated yet.

Implemented:

- project bootstrap and configuration loading
- SQLite schema and database access layer
- Winamax summary parser
- Winamax hand history parser
- file watcher component
- database import service
- Tkinter desktop dashboard
- automated tests for setup, database, parser, watcher, importer, logging, and statistics

Not fully wired yet:

- the watcher is not yet connected to the importer in the running desktop app
- the UI currently reads from the database, but it does not yet trigger live imports or auto-refresh from filesystem events
- advanced tournament and bankroll analytics are not implemented yet

## Project Structure

```text
poker_tracker/
├── bootstrap.py
├── main.py
├── logging_system.py
├── config/
│   └── config.json
├── database/
│   ├── __init__.py
│   ├── database.py
│   ├── importer.py
│   └── models.py
├── parser/
│   ├── hand_parser.py
│   └── tournament_parser.py
├── statistics/
│   └── calculator.py
├── ui/
│   ├── dashboard.py
│   ├── hands_view.py
│   └── tournaments_view.py
├── watcher/
│   └── file_watcher.py
└── tests/
```

## Requirements

- Python 3.12+
- Tkinter available in your Python installation

On Linux, Tkinter is usually installed through the system package manager, not through `pip`.

Examples:

- Debian/Ubuntu: `sudo apt install python3-tk`
- Fedora: `sudo dnf install python3-tkinter`
- Arch: `sudo pacman -S tk`

## Installation

Create and activate a virtual environment, then install the project from `pyproject.toml`.

```bash
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

## Configuration

Edit [config/config.json](/home/sesa781182/pers/poker_tracker/config/config.json) before running the app.

Example:

```json
{
  "player_name": "MyPseudo",
  "winamax_folder": "C:/Users/YourUser/AppData/Roaming/winamax/documents",
  "database_path": "data/poker_tracker.db",
  "log_directory": "logs"
}
```

Meaning:

- `player_name`: hero/player name used by the UI statistics
- `winamax_folder`: Winamax hand history directory to monitor later
- `database_path`: SQLite database path
- `log_directory`: directory where log files are written

## How To Use It

### 1. Run the desktop application

```bash
python main.py
```

The app will:

- load the config
- initialize logging
- initialize the SQLite database
- open the Tkinter dashboard

If the database is empty, the UI will open but show no imported data yet.

### 2. Import Winamax files into the database

The importer exists, but there is not yet a CLI command or menu action for it. For now, use a short Python snippet.

```bash
python - <<'PY'
from pathlib import Path

from bootstrap import bootstrap_application, load_config, resolve_config_path
from database.importer import DatabaseImporter

config = load_config()
database = bootstrap_application()
importer = DatabaseImporter(database)

project_root_config = Path("config/config.json")
winamax_folder = resolve_config_path(project_root_config, config["winamax_folder"])

for path in sorted(winamax_folder.glob("*.txt")):
    report = importer.import_file(path)
    print(path.name, report.status, report.hands_imported, report.tournaments_imported)
PY
```

You can also import a single file:

```bash
python - <<'PY'
from pathlib import Path

from bootstrap import bootstrap_application
from database.importer import DatabaseImporter

database = bootstrap_application()
importer = DatabaseImporter(database)
report = importer.import_file(Path("samples/20260628_Freeroll(1119027769)_real_holdem_no-limit.txt"))
print(report)
PY
```

### 3. Use the dashboard

Once data is imported, the UI currently shows:

- total hands played
- number of tournaments seen in the hands table
- cumulative hand result
- recent hands list
- recent tournaments list
- VPIP
- PFR
- limp percentage
- aggression factor
- showdown win percentage

## Logging

Log files are created in the configured `log_directory`.

Current log files:

- `app.log`
- `database.log`
- `parser.log`
- `watcher.log`
- `imports.log`

## Testing

Run the full test suite with:

```bash
pytest
```

Current tests cover:

- bootstrap and configuration
- database layer
- parsers
- file watcher
- importer
- logging setup
- statistics calculation