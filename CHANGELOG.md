# Changelog

All notable changes to MyPokerTracker are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-08-31

### Added

- Rake calculation for cash-game hands.
- Ante calculation for tournament hands.
- Re-entries tracking for tournament hands.
- Auditable tournament entry costs and settlement reconciliation through a shared accounting service.
- EUR result charts for All, Tournament, and Expresso scopes, plus a BB/EUR selector for Cash.
- Visible chart reset controls and UTC-labeled result hover details.
- A unified Sessions activity view for cash sessions and tournament or Expresso summaries, including entry costs, payment source, winnings, EUR result, and cash BB result.

### Fixed

- Preserve original source indexes and important extrema when zooming charts with more than 1,200 points.
- Include tournament entry and re-entry debits as separate chronological bankroll events.
- Replace combinable mode checkboxes with a deterministic All, Cash, Tournament, or Expresso selection and mode-specific headline metrics.
- Label displayed hand, session, tournament, and chart timestamps consistently as UTC.
- Make one click select any activity for its overview and double-click open its hand list for both cash sessions and tournaments.

## [0.5.1] - 2026-08-28

### Fixed

- Fixed an issue where the dashboard would not refresh correctly after importing large hand-history files.
- Import large hand-history files in a single SQLite transaction to avoid per-hand database commits and improve dashboard load time.
- Limit BB-chart rendering density for large cash-game histories while retaining the complete calculation history.
- Bounty winning parsing now correctly handles bounty amounts with a decimal point, e.g., `You won Bounty 0.13€`.

## [0.5.0] - 2026-08-21

### Added

- Add a manually verified mixed-mode calculation regression covering cash BB, tournament and Expresso profit, and chronological bankroll totals.
- Replace the dashboard bankroll graph with an interactive cash-game BB graph with range-selection zoom, hover details, and direct hand-detail navigation.
- Add per-hand BB results derived from each hand's recorded big blind and displayed in hand history, including tournament and Expresso chip-BB results.
- Add a dedicated advanced Statistics tab with filtered hand-outcome, VPIP, PFR, aggression, sampled preflop 3-Bet/4-Bet and all-in rates, and cash-game BB metrics.
- Persist Winamax all-in action flags and reimport unchanged hand histories once so all-in metrics can use durable source data.

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

[0.6.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.6.0
[0.5.1]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.5.1
[0.5.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.5.0
[0.4.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.4.0
[0.3.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.3.0
[0.2.1]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.2.1
[0.2.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.2.0
[0.1.0]: https://github.com/QuentinBNP/poker_tracker/releases/tag/v0.1.0