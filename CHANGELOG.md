# Changelog

All notable changes to MyPokerTracker are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-03

### Added

- Windows uninstaller support.
- In-app Settings dialog to edit and save the player name, Winamax folder, database path, and log folder.

### Changed

- Centralized release versioning in `pyproject.toml`.
- Moved application source code to `src/`.
- New installations detect a single Winamax account folder and use its account name and history folder as defaults.
- Startup now imports existing Winamax hand-history and tournament-summary files instead of waiting for a later file change.
- Tournament chip results are tracked and displayed in big blinds, while cash-game and tournament prize results are tracked separately as money profit or loss.

## [0.1.0] - 2026-07-30

### Added

- Winamax hand-history and tournament-summary imports.
- Local SQLite storage, dashboard, statistics, and file watching.
- Windows executable and installer build support.

[0.2.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.2.0
[0.1.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.1.0