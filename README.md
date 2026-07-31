# MyPokerTracker

[![CI](https://github.com/QuentinBNP/poker_tracker/actions/workflows/pytest.yml/badge.svg)](https://github.com/QuentinBNP/poker_tracker/actions/workflows/pytest.yml)
[![Coverage](https://codecov.io/gh/QuentinBNP/poker_tracker/graph/badge.svg)](https://codecov.io/gh/QuentinBNP/poker_tracker)

MyPokerTracker is a personal Winamax desktop tracker written in Python.

Current packaged Windows builds use the bundled MyPokerTracker icon and embed Windows version metadata in the generated executable and installer.

Tagged releases are built by [.github/workflows/tag.yaml](/home/sesa781182/pers/poker_tracker/.github/workflows/tag.yaml) and publish the Windows installer when you push a tag.

## Releases

The version in `pyproject.toml` is the single source of truth for the application, Windows executable, and installer. Before releasing, update that version and [CHANGELOG.md](/home/sesa781182/pers/poker_tracker/CHANGELOG.md), then create the matching `vX.Y.Z` tag. The release workflow rejects tags that do not match the project version.

## Installed Windows Data

The installed application creates its editable configuration at `%APPDATA%\MyPokerTracker\config.json`, usually `C:\Users\<your-user>\AppData\Roaming\MyPokerTracker\config.json`.

Its database and logs are stored separately at `%LOCALAPPDATA%\MyPokerTracker`, usually `C:\Users\<your-user>\AppData\Local\MyPokerTracker`. Uninstalling the application removes the installed program but keeps these files. To completely remove MyPokerTracker, delete both folders after uninstalling.

Use the Start Menu entry `MyPokerTracker > Uninstall MyPokerTracker` to uninstall a future release. The existing 0.1.0 installation can be removed from Windows Settings > Apps > Installed apps, or by running `unins000.exe` from its MyPokerTracker installation folder.

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
├── scripts/
│   ├── import_winamax_files.py
│   ├── build_windows_exe.py
│   └── build_windows_installer.py
├── .github/workflows/scripts/
│   ├── run_main_briefly.py
│   ├── smoke_test_ui.py
│   └── verify_release_version.py
├── config/
│   └── config.json
├── src/
│   ├── app_info.py
│   ├── bootstrap.py
│   ├── logging_system.py
│   ├── main.py
│   ├── database/
│   ├── parser/
│   ├── poker_stats/
│   ├── ui/
│   └── watcher/
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

## Windows Quick Start

On Windows, install Python 3.11 or newer from the official Python installer and keep the default `tkinter` support enabled.

Create and activate a virtual environment from PowerShell:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Then update `%APPDATA%\MyPokerTracker\config.json` with your real Winamax history folder, for example:

```json
{
  "player_name": "MyPseudo",
  "winamax_folder": "C:/Users/YourUser/AppData/Roaming/winamax/documents",
  "database_path": "data/poker_tracker.db",
  "log_directory": "logs"
}
```

Start the desktop app with:

```powershell
python src/main.py
```

If you want the dashboard to show real data immediately, import files first:

```powershell
python scripts/import_winamax_files.py
```

Note: the current app opens the dashboard and database, but live file watching is not yet wired into the running UI.

## Configuration

For the installed Windows application, edit `%APPDATA%\MyPokerTracker\config.json`. The repository [config/config.json](/home/sesa781182/pers/poker_tracker/config/config.json) is only for local development with an explicit config path.

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
python src/main.py
```

The app will:

- load the config
- initialize logging
- initialize the SQLite database
- open the Tkinter dashboard

If the database is empty, the UI will open but show no imported data yet.

### 2. Import Winamax files into the database

The importer exists as a script, but there is not yet a UI menu action for it.

```bash
python scripts/import_winamax_files.py
```

You can also import a single file:

```bash
python scripts/import_winamax_files.py samples/20260628_Freeroll(1119027769)_real_holdem_no-limit.txt
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

## Git Hook

This repository includes a plain Git pre-commit hook that runs `ruff check .` and `mypy .` through a repo script.

Enable it once per clone with:

```bash
git config core.hooksPath .githooks
```

You can also run the same checks manually at any time:

```bash
./scripts/run_quality_checks.sh
```

## Coverage And Badges

The CI workflow already generates:

- line coverage
- branch coverage
- `coverage.xml`
- `htmlcov/`

The README badge above uses Codecov. To make it work reliably:

1. Enable the repository on Codecov.
2. Keep the `Upload coverage to Codecov` step in the GitHub Actions workflow.
3. If the repository is private, add a `CODECOV_TOKEN` repository secret in GitHub and configure Codecov to use it.

Important limitation: `pytest-cov` and `coverage.py` report line and branch coverage, but they do not provide a standard functional coverage metric. If you want "functional coverage", that usually means tracking tested features or scenarios separately, not a built-in Python coverage percentage.