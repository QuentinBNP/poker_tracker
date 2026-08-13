# Changelog

All notable changes to MyPokerTracker are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Classify and persist Winamax Expresso summaries separately from tournaments, including a cache-format upgrade that reimports unchanged files once.

### Added

- Allow the dashboard scope to combine Cash, Tournament, and Expresso modes, with an All option for the complete history.
- Add filtered session history. Selecting a session opens its hands in chronological order.

## [0.4.0] - 2026-08-07

### Fixed

- Reimport cached Winamax files when the importer format changes, allowing upgraded installations to recover hand data that was not persisted by an earlier importer version.

### Changed

- Redesigned the dashboard around global game-mode and date filters, mode-appropriate performance metrics, selected bankroll results, and filtered recent history.
- Added an interactive native bankroll chart with source-linked hover details, wheel zoom, and drag panning.

## [0.3.0] - 2026-08-07

### Added

- Added persisted game-mode classification, session records, session backfill for existing databases, and database indexes required for upcoming history and filter queries.
- Added shared date, game-mode, table, and tournament filters for hand, action, and tournament repository queries.
- Added a filter-aware statistics service with cash-game BB/100 plus tournament and Expresso profit and ROI metrics.
- Added a filter-aware bankroll service that produces chronological, source-linked cash-game, tournament, and Expresso result points.

### Changed

- Improve importer with cache to avoid re-importing already imported files.

## [0.2.1] - 2026-08-03

### Changed

- Added automatic SQLite migrations for existing databases, including the chip big-blind and tournament-winnings columns introduced in 0.2.0.
- Fixed the Windows installer shortcut template so it compiles correctly and uses a versioned installed icon file, preventing stale shortcut icons after upgrades.

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


[0.4.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.4.0
[0.3.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.3.0
[0.2.1]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.2.1
[0.2.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.2.0
[0.1.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.1.0