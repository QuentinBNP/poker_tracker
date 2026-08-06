# Version 2 Phase 1 Review

Status: complete on 2026-08-06.

This review documents the existing MVP before the Version 2 data-model work begins. It is based on the current implementation and tests; it does not change application behavior.

## Current Architecture

The running application is assembled in `src/main.py`:

```text
Tkinter dashboard
    -> Database
    -> SQLite

Winamax file watcher
    -> DatabaseImporter
    -> parsers
    -> Database
    -> dashboard refresh
```

`src/bootstrap.py` loads configuration, configures logging, initializes the database, and returns the `Database` instance. `src/main.py` starts the watcher, imports existing and newly detected files through `DatabaseImporter`, and refreshes the dashboard after a successful import.

The UI reads through `Database` and `StatisticsCalculator`; it does not issue SQL itself. This separation should be retained. New Version 2 read models and calculations belong in services/repositories rather than Tkinter widgets.

## Current SQLite Schema

The schema and existing additive migration mechanism are in `src/database/database.py`.

| Table | Stable identifier | Current purpose | Relationships |
| --- | --- | --- | --- |
| `tournaments` | `tournament_id` (unique) | Tournament summary and prize result | Referenced by `hands.tournament_id` |
| `hands` | `hand_id` (unique) | One parsed hand with timestamp, table, hero, cards, board, pot, chip result, and big blind | Optionally belongs to a tournament |
| `players` | `name` (unique) | Imported player names | No foreign key to a hand or action |
| `actions` | auto-increment `id` | Ordered parsed actions with player, street, action, and amount | References `hands.hand_id` |
| `imports` | `filename` (unique) | Import status and file cache metadata | No foreign key |

Existing persisted fields relevant to Version 2:

- `hands.played_at`, `hands.table_name`, `hands.tournament_id`, `hands.result`, and `hands.big_blind` support initial classification, sessions, filtering, and per-hand BB calculations.
- `tournaments.started_at`, `tournaments.finished_at`, `tournaments.buy_in`, `tournaments.position`, `tournaments.winnings`, and `tournaments.bounty_winnings` support tournament result and duration calculations.
- `actions` are persisted in insertion order and can be reloaded per stable hand ID.

The current migrator only adds missing columns with `ALTER TABLE`; it does not delete or recreate existing tables. Tests in `tests/test_database.py` verify the existing `big_blind`, `winnings`, and `bounty_winnings` migration. Phase 2 should extend this additive strategy with ordered, named migrations and tests against a pre-Version-2 database.

Current schema gaps for the Version 2.0/2.5 guide:

- No persisted `game_mode`, `session`, `session_id`, or session boundaries.
- No indexes beyond SQLite unique-constraint indexes. Queries need indexes for filters such as played time, hand ID, tournament ID, game mode, session ID, and table name.
- No stored per-hand `result_bb`; it must currently be derived from `result / big_blind` when `big_blind > 0`.
- Players are global names only. Seat, stack, button position, bounty, known cards, and player-to-hand membership are parsed but discarded during import.
- Actions store no original sequence value beyond auto-increment ID, no action-specific cards, no all-in flag, and no action result/pot snapshot.
- Raw imported source text is not retained.

## Parser and Import Review

`src/parser/hand_parser.py` returns dictionaries for tournament and cash-game hands. It extracts:

- hand ID, UTC play time, table name, tournament ID when available, tournament name, buy-in, and a two-value mode label (`tournament` or `cashgame`)
- hero cards, final board, total pot, net chip/money result, and big blind
- player seat, stack, bounty, and dealer-button data
- actions by street, including shown cards and all-in data when present
- winner names

`src/parser/tournament_parser.py` returns tournament metadata, duration, position, Winamax mode/type/speed text, and winnings including bounty winnings.

`src/database/importer.py` writes only the `Hand`, `Tournament`, global `Player`, and simplified `Action` models. It creates a placeholder tournament when a hand arrives before its summary. The importer therefore already links tournament hands to their tournament with `tournament_id`, while cash hands have `NULL` in that column.

Classification is currently not adequate for the target `CASH_GAME`, `TOURNAMENT`, and `EXPRESSO` modes: it is not persisted, uses `cashgame` instead of the target name, and has no Expresso-specific classification. The next phase must classify from Winamax hand and summary data during import, not from UI selection.

For replay, the parser has some required source data but import currently loses essential details. Phase 2 should preserve the minimum durable structured fields needed for later replay before the replay UI is attempted. Unknown opponent cards must remain unknown; no source currently supports reconstructing them.

## Current Statistics and UI

`src/poker_stats/calculator.py` calculates overall MVP metrics for one configured hero: hand count, tournament count, cash result, tournament profit, chip result in BB, VPIP, PFR, limp percentage, aggression factor, and showdown win percentage.

`src/ui/dashboard.py` presents those overall values and recent hands/tournaments. `src/ui/hands_view.py` and `src/ui/tournaments_view.py` display the most recent rows supplied by the dashboard.

Current limitations relevant to Version 2:

- The query methods are dashboard-specific and use fixed recent-row limits; there is no shared filter object, pagination, or history search.
- Metrics mix overall hand/action analysis with unfiltered tournament data. The dashboard has no date or game-mode selection.
- Showdown wins are matched only against the most recent 500 hands, so this metric is not suitable as a complete historical aggregate.
- There is no bankroll time series, chart, session view, dedicated statistics page, tournament filter, cash history, Expresso history, hand detail, or replay navigation.

## Compatibility Constraints

Phase 2 must preserve these existing facts:

- Existing `hand_id` and `tournament_id` values are the stable links for imported MVP data.
- Existing database files must be upgraded in place; no table drop or destructive reset is acceptable.
- A tournament can be created from a hand before its summary, then updated when the summary is imported.
- A cash-game hand is currently identified by missing `tournament_id`; this is useful migration input but is not sufficient alone to distinguish all future modes.
- Existing import-cache behavior is keyed by filename plus modification time and size. Any backfill strategy must deliberately account for imports that would otherwise be skipped.

## Phase 2 Status

Phase 1 is complete because the current schema, parser outputs, import path, statistics, UI, existing tournament linkage, and data gaps are documented above.

Phase 2 is complete. The implementation now persists the canonical `CASH_GAME`, `TOURNAMENT`, and `EXPRESSO` modes; creates sessions; assigns newly imported hands to those sessions; backfills legacy hand modes and sessions in place; and adds indexes for the planned history and filtering queries.

Tournament and Expresso hands share one session per tournament ID. Cash-game hands at the same table and mode remain in one session when their timestamps are no more than 30 minutes apart; a larger gap starts a new session. The classification and migration/backfill behavior are covered by deterministic parser, database, and importer tests.

Phase 3 is next: implement a shared filtering layer for date, mode, table, and tournament constraints. It should use the persisted `game_mode`, `session_id`, `played_at`, `table_name`, and `tournament_id` fields instead of duplicating filter logic in Tkinter views.

Verification note: the configured test suite could not be run in this environment because the `pytest` executable is not installed in the active shell. No conclusion about the current test outcome was made.