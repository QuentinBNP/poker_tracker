# Hand Reviewer and Qt UI Migration Plan

## 1. Goal

Add an accurate, local hand reviewer and migrate MyPokerTracker from Tkinter to a
modern Windows desktop UI without losing existing data or features.

The reviewer is for historical analysis only. It must not provide real-time advice,
interact with the Winamax client, or automate play.

This plan extends the replay requirements in
`.github/instructions/poker_tracker_improvements.md`, especially sections 19-28 and
the Version 2.5 implementation order.

## 2. Fixed Architecture Decisions

### 2.1 Repository strategy

Keep the reviewer and new UI in this repository.

Reasons:

- The reviewer directly depends on the existing parser, SQLite migrations, sessions,
  filters, actions, and stable hand IDs.
- One repository keeps schema, parser, replay engine, UI, tests, and Windows packaging
  on compatible versions.
- A Git submodule or separate repository would add release coordination without
  creating a useful runtime boundary.

Create internal packages instead:

```text
src/
  database/             Existing persistence and migrations
  parser/               Existing Winamax parsing
  poker_stats/          Existing accounting and statistics
  replay/               New UI-independent replay domain
    models.py
    replay_service.py
    state_engine.py
  ui/                    Existing Tkinter UI during transition
  ui_qt/                 New PySide6 UI
    application.py
    design_system.py
    dashboard/
    history/
    reviewer/
    settings/
```

### 2.2 UI technology

Use PySide6 and Qt Widgets for the new desktop UI.

- Use standard Qt widgets for navigation, filters, forms, tables, and dialogs.
- Use `QGraphicsView`/`QGraphicsScene` for the poker table.
- Keep replay and accounting logic free of Qt imports.
- Do not introduce a web server, browser runtime, Node.js, React, or Tauri.
- Do not remove Tkinter until the Qt application passes the feature-parity gate.

The first implementation task must pin and validate a supported PySide6 version on
Python 3.11 and 3.12, Linux CI, Windows CI, and PyInstaller before committing to it.

### 2.3 Migration strategy

Use an incremental replacement, not a rewrite:

1. Preserve the current Python services and SQLite database.
2. Add the structured replay data and engine.
3. Add a Qt application beside the Tkinter application.
4. Build the reviewer as the first complete Qt workflow.
5. Migrate existing screens one at a time.
6. Switch the packaged entry point only after feature parity.
7. Remove Tkinter only after one stable Qt release and explicit approval.

## 3. Current Capability Baseline

The following behavior exists before this project starts and must be preserved.

### 3.1 Application and import

- MyPokerTracker naming, icon, version metadata, executable, and installer.
- `%APPDATA%\MyPokerTracker\config.json` configuration.
- `%LOCALAPPDATA%\MyPokerTracker` database and logs.
- Automatic additive SQLite migrations; no database deletion on upgrade.
- Startup scan and import of existing Winamax files.
- Live Winamax folder watching, import, and dashboard refresh.
- Import caching and format-version reprocessing.
- Settings for player name, Winamax folder, database path, and log folder.
- Application, database, watcher, parser, and import logging.

### 3.2 Data and accounting

- `CASH_GAME`, `TOURNAMENT`, and `EXPRESSO` classification from source data.
- Stable hand IDs and tournament links.
- Cash sessions and tournament/Expresso activities.
- Per-hand big blind, EUR result, BB result, pot, board, hero cards, and rake.
- Tournament entries and re-entries with nominal buy-in, actual cash cost, payment
  method, and persisted free-entry correction.
- Chronological accounting events and tournament reconciliation.
- Cash rake reporting without subtracting rake twice.
- Correct separation of EUR, BB, and ROI metrics.

### 3.3 User interface

- Single-choice All, Cash, Tournament, and Expresso scope.
- Global period and custom UTC date filters.
- All-mode combined EUR accounting.
- Cash BB chart with EUR toggle.
- Tournament and Expresso EUR charts.
- Chart sampling that retains source indexes, endpoints, minimum, and maximum.
- Chart zoom, hover details, reset, and hand-ID linkage.
- Mode-specific dashboard headline metrics.
- Detailed poker statistics page.
- Unified Sessions activity view, including summary-only tournaments.
- One-click activity overview and double-click hand-list navigation.
- Ordered hand list and basic hand details/actions dialog.
- Persisted free-entry correction from tournament activity.
- UTC labels on displayed timestamps.

### 3.4 Engineering and release

- Linux and Windows pytest jobs.
- Coverage reports and Codecov upload.
- Ruff and mypy quality script and pre-commit hook.
- Linux and Windows UI smoke tests.
- PyInstaller Windows build and Inno Setup installer.
- Tagged release workflow with version/tag verification.

## 4. Current Replay Data Gaps

The hand parser currently observes information that is not fully persisted. The new
UI must not be built on incomplete or inferred state.

Known gaps:

- Player seats, initial stacks, bounties, and dealer button are parsed but not stored
  per hand.
- Blinds and antes affect accounting but are removed from persisted action history.
- Action order relies on row insertion order rather than an explicit sequence.
- Shown opponent cards and hand descriptions are parsed but not stored.
- Raise source amount and target amount are not both retained.
- Uncalled returned bets are not represented as replay actions.
- Original hand text/source is not available for replay auditing.
- Existing `players` rows identify names globally, not participation in one hand.

Consequences:

- Existing enriched source files must be re-imported after the schema upgrade.
- Legacy hands whose source files are unavailable remain usable for statistics and
  basic details, but the reviewer must mark unavailable facts as `Unknown`.
- The reviewer must never infer unknown hole cards or fabricate missing actions.

## 5. Target Replay Data Contract

### 5.1 Domain models

Add immutable, typed models under `src/replay/`:

```text
ReplayHand
  hand_id
  game_mode
  occurred_at
  table_name
  hero_name
  big_blind
  board_cards
  players
  actions
  winners
  final_pot

ReplayPlayer
  seat
  name
  starting_stack
  bounty
  is_dealer
  is_hero
  known_hole_cards | None

ReplayAction
  sequence_number
  street
  player
  action_type
  amount | None
  target_amount | None
  cards | None
  description | None
  is_all_in

ReplayState
  action_index
  street
  visible_board
  players and current stacks
  folded/all-in state
  street commitments
  total commitments
  pot
  current actor
  last action
```

All monetary/chip calculations must use one documented amount convention. Raises
must retain enough information to distinguish the increment from the total target.

### 5.2 Additive persistence

Add a `hand_players` table:

| Field | Requirement |
| --- | --- |
| `hand_id` | Foreign key to `hands.hand_id` |
| `seat` | Original Winamax seat number |
| `player_name` | Source player name |
| `starting_stack` | Stack before actions |
| `bounty` | Optional source bounty |
| `is_dealer` | Dealer-button source fact |
| `is_hero` | Hero identity for this hand |
| `known_hole_cards` | Nullable; never inferred |

Extend `actions` additively with:

- `sequence_number INTEGER`
- `target_amount REAL`
- `cards TEXT`
- `description TEXT`
- an explicit action type for returned uncalled bets

Add optional replay provenance to `hands` or a linked source table:

- source filename
- original hand text, or an equivalent durable source snapshot
- parser/import format version

Add indexes for `hand_players.hand_id` and `actions(hand_id, sequence_number)`.

Do not persist derived replay frames. They must be deterministically produced from
the source facts by the replay engine.

### 5.3 Migration rules

- Add schema elements through the existing migration mechanism.
- Never delete or recreate the user's database.
- Existing hands, results, sessions, and accounting values must remain unchanged.
- Existing action rows receive deterministic sequence numbers in current row order.
- Increase `DatabaseImporter.IMPORT_FORMAT_VERSION` once the enriched parser and
  persistence path are ready.
- Re-import available source histories to enrich replay data.
- Preserve manual tournament entry corrections during re-import.
- Mark incomplete legacy replay data as incomplete; do not fail the whole hand.

## 6. Replay Engine Requirements

`ReplayService` loads structured source facts from the database. `ReplayStateEngine`
produces the initial state and one state after every action.

It must support:

- antes, small blind, and big blind;
- folds, checks, calls, bets, raises, and all-ins;
- uncalled bet returns;
- flop, turn, river, and showdown transitions;
- main-pot and side-pot collection events;
- known shown cards and unknown cards;
- multiple winners and split pots when present in source data;
- cash, tournament, and Expresso chip units;
- partial/malformed histories through explicit incomplete-state diagnostics.

Engine invariants:

- Action ordering is stable and reproducible.
- A stack never becomes negative.
- Folded players never act later unless the source is flagged inconsistent.
- Pot and commitment changes are explainable by source actions.
- Final stack/result reconciliation is checked when enough data exists.
- Missing data yields `Unknown` or an audit warning, never invented state.

## 7. Hand Reviewer Experience

### 7.1 Entry points

The reviewer must open from:

- a hand in the Hands page;
- a hand in a cash session, tournament, or Expresso hand list;
- a source-linked BB chart point;
- a source-linked EUR cash-hand chart point.

Tournament entry and settlement points without a hand ID open tournament activity,
not an invented hand.

### 7.2 Layout

Use a work-focused desktop layout:

```text
+----------------------------------------------------------------+
| Session / event | Hand 12 of 42 | First Prev Next Last          |
+-----------------+----------------------------------------------+
| Ordered hands   | Poker table and current street               |
|                 |                                              |
|                 +----------------------------------------------+
|                 | Action timeline and audit details            |
+-----------------+----------------------------------------------+
| Previous action | Play/Pause | Next action | Known cards toggle|
+----------------------------------------------------------------+
```

The table must show:

- players in original seats;
- hero and dealer button;
- starting/current stacks;
- known hero cards;
- known opponent cards only when the source contains them and the toggle is enabled;
- `??` for unknown opponent cards;
- visible community cards for the current street;
- current pot, street, active actor, and latest action;
- folded and all-in states;
- final winner/result when replay reaches completion.

The adjacent textual history must remain visible for source auditing.

### 7.3 Navigation and interaction

- First, previous, next, and last hand controls.
- Previous action, next action, play/pause, and restart controls.
- Optional speed selection only after manual stepping is correct.
- `Left`/`Right`: previous/next action.
- `Ctrl+Left`/`Ctrl+Right`: previous/next hand.
- `Home`/`End`: first/last action in the current hand.
- Selecting an action jumps to its exact replay state.
- Navigation does not require returning to Sessions.
- Selected session, hand, and action remain visible in their lists.

## 8. Qt Visual Direction

The Qt application should be modern but remain an analytics tool rather than a
marketing interface.

- Use a compact left navigation rail and a stable top filter bar.
- Prefer dense tables and unframed page sections over decorative card grids.
- Use a neutral light theme first, with strong contrast and restrained accent colors.
- Define design tokens for color, spacing, typography, radius, and chart colors.
- Use one bundled, redistributable typeface or a documented Windows-safe fallback.
- Use familiar icons with tooltips for navigation and replay controls.
- Support keyboard navigation, visible focus, high DPI, and 125%/150% Windows scaling.
- Avoid layout shifts when values, labels, cards, or player names change.
- Keep result colors semantically consistent across dashboard, charts, and reviewer.

Dark mode is optional after feature parity; it is not a migration blocker.

## 9. UI Migration Sequence

### Phase 0: Decision record and packaging spike

Deliverables:

- Record the one-repository and PySide6 decision.
- Add PySide6 and Qt test tooling in a dedicated dependency group or documented main
  dependency strategy.
- Build a minimal Qt window on Linux and Windows CI.
- Package and launch a PyInstaller Qt executable on Windows.
- Measure installer size and cold-start behavior against the Tkinter release.

Acceptance criteria:

- Qt starts on supported Python versions and both CI operating systems.
- The Windows artifact launches without missing Qt plugins.
- Existing Tkinter startup and release build remain operational.
- The selected PySide6 version and licensing note are documented.

### Phase 1: Replay parser contract

Deliverables:

- Typed parser output for players and replay actions.
- Parsing of forced bets, shown cards, descriptions, all-ins, collections, and
  uncalled returns.
- Sanitized cash, tournament, Expresso, fold, showdown, all-in, split-pot, side-pot,
  missing-card, and malformed fixtures.

Acceptance criteria:

- Every action has an explicit source order.
- Seat, stack, dealer, cards, and action amounts match fixture text exactly.
- Unknown cards remain `None`/`Unknown`.
- Existing result, rake, BB, and statistics parser tests remain unchanged and green.

### Phase 2: Replay persistence and migration

Deliverables:

- Additive schema and indexes.
- Repository methods for loading one hand and an ordered session hand list.
- Importer support and import-format upgrade.
- Legacy-data completeness indicator.

Acceptance criteria:

- Upgrading a copy of an existing database preserves all row counts and accounting
  totals before replay enrichment.
- Re-import enriches replay facts without duplicating hands/actions or overwriting
  manual free-entry corrections.
- A missing source file leaves the legacy hand reviewable in reduced detail.
- Querying a hand does not require parsing raw text in the UI.

### Phase 3: Replay state engine

Deliverables:

- UI-independent state engine and replay service.
- Reconciliation diagnostics for incomplete or inconsistent source data.
- Unit tests for every action and street transition.

Acceptance criteria:

- Known fixtures produce exact stacks, commitments, board, pot, and winner at every
  action index.
- First and final states reconcile with source data where sufficient facts exist.
- Side pots, split pots, uncalled returns, folds, and all-ins have deterministic tests.
- The replay package has no Tkinter or PySide6 imports.

### Phase 4: Qt shell and design system

Deliverables:

- Qt application entry point and application controller.
- Navigation rail, global mode/date filters, settings access, and design tokens.
- Thread-safe import/watcher notifications using Qt signals at the UI boundary.
- Error reporting and logging equivalent to the current application.

Acceptance criteria:

- The shell opens the existing database and configuration paths.
- Startup import and live watching do not block the UI thread.
- Closing the app stops the watcher cleanly.
- Controls remain usable at 1366x768 and 1920x1080 with 100%, 125%, and 150% scale.

### Phase 5: Reviewer vertical slice

Deliverables:

- Session/event hand browser.
- Poker-table scene, action timeline, controls, shortcuts, and known-card toggle.
- Basic and incomplete-data states.

Acceptance criteria:

- Double-clicking any activity opens its ordered hands.
- Selecting a hand opens the reviewer at its initial state.
- The user can navigate first-to-last hands without returning to history.
- Every action can be reached manually and produces the tested engine state.
- Opponent cards appear only when explicitly known and enabled.
- Unknown cards display `??`; malformed data displays an audit warning.

### Phase 6: Existing screen migration

Migrate in this order:

1. Hands and Sessions/activity.
2. Dashboard and global filters.
3. EUR and BB charts.
4. Statistics.
5. Settings and import status.

Acceptance criteria:

- Each screen passes its row in the feature-parity matrix before the next screen is
  declared complete.
- Business calculations remain in services/repositories, not Qt widgets.
- Lists use SQL limits/pagination and do not load all hands for display.
- Chart points retain original source IDs and source indexes.
- Existing UTC display policy remains unchanged.

### Phase 7: Default UI switch

Deliverables:

- Make Qt the default `main.py` UI.
- Update PyInstaller collection rules, UI smoke scripts, CI, and installer validation.
- Keep a documented temporary Tkinter fallback entry point for one stable release.

Acceptance criteria:

- The complete feature-parity matrix passes on Windows.
- Installation over the previous release retains config, database, corrections, and
  logs.
- The packaged app starts, imports, watches, refreshes, closes, and restarts cleanly.
- No user workflow requires the Tkinter fallback.

### Phase 8: Tkinter retirement

This phase requires explicit approval after a stable Qt release.

Acceptance criteria:

- No production import references `src/ui/`.
- Equivalent Qt tests and smoke coverage exist for every removed workflow.
- Tkinter dependencies and CI packages are removed only after fallback retirement.
- Release notes identify the removal and supported upgrade path.

## 10. Feature-Parity Matrix

Every row must be marked `PASS` on source execution and packaged Windows execution
before Qt becomes the default.

| Capability | Required Qt behavior | Verification |
| --- | --- | --- |
| Configuration | Reuse current paths and settings | Existing config fixture + upgrade smoke |
| Database migration | Open and upgrade existing DB in place | Snapshot migration test |
| Startup import | Process existing source files | Import integration test |
| Live watcher | Import changed files and refresh UI | Watcher integration + UI smoke |
| Import cache | Skip unchanged current-format files | Existing importer tests |
| Logging | Preserve all configured logs | Logging tests + packaged smoke |
| Mode scope | All/Cash/Tournament/Expresso single choice | Qt model/UI test |
| Date filters | All presets and custom UTC range | Shared filter tests |
| All accounting | Combined chronological EUR result | Accounting contract test |
| Cash metrics | Hands, EUR, BB, BB/100 | Statistics fixture |
| Tournament metrics | Events, cost, winnings, profit, ROI, re-entries | Statistics fixture |
| Expresso metrics | Games, cost, winnings, profit, ROI, tickets | Statistics fixture |
| Free entry | View and persist correction | DB + Qt interaction test |
| Dashboard | Preserve mode-specific headline values | View-model test |
| EUR chart | Zoom, hover, reset, source metadata | Chart model + UI test |
| BB chart | Zoom, hover, reset, hand ID, extrema | >1,200-point regression |
| Sessions | Include cash and summary-only events | Repository + UI test |
| Activity interaction | Click overview; double-click hands | Qt interaction test |
| Hands | Ordered list with EUR/BB details | Repository + UI test |
| Basic details | Cards, board, pot, result, actions | Fixture + UI test |
| Statistics | Preserve current advanced metrics/sample rules | Existing service + Qt model tests |
| UTC policy | Label every displayed timestamp UTC | Formatter and UI scan tests |
| Settings | Save and apply all existing settings | Qt interaction test |
| Windows identity | Preserve MyPokerTracker name/icon/metadata | Build asset tests |
| Installer | Upgrade without deleting user data | Windows installation smoke |
| Release workflow | Tag/version match and publish installer | Workflow validation |

## 11. Testing and Quality Strategy

### 11.1 Automated test layers

- Parser fixture tests for exact source extraction.
- Migration tests using copies of pre-reviewer databases.
- Repository tests for ordered, paginated hand/session retrieval.
- Replay engine tests for every state transition and invariant.
- Service tests for session-to-hand and graph-to-hand navigation.
- Qt view-model tests without rendering where possible.
- Qt widget interaction tests for navigation, filters, and reviewer controls.
- Screenshot smoke tests at representative sizes and Windows scaling levels.
- Packaged Windows launch and upgrade smoke tests.

Use a Qt-specific test dependency such as `pytest-qt` only after the packaging spike
confirms the selected stack.

### 11.2 Required commands

Each phase must pass:

```bash
pytest
./scripts/run_quality_checks.sh
```

Before a Qt release, also pass:

```bash
python scripts/build_windows_installer.py
```

The CI equivalent must run on Windows. Native Qt UI smoke tests must replace, not
silently remove, the existing Tkinter smoke coverage when Qt becomes default.

### 11.3 Manual validation set

Maintain anonymized fixtures and manually compare reviewer states with the original
Winamax histories for:

- heads-up and multi-player hands;
- cash, tournament, and Expresso;
- folds before showdown;
- known and unknown opponent cards;
- all-ins on each street;
- uncalled returns;
- main and side pots;
- split pots;
- antes and blinds;
- incomplete or malformed histories.

## 12. Documentation and Changelog Requirements

### 12.1 README

README maintenance is part of implementation, not a final cleanup task.

Before Phase 1, update the current-capabilities section because it is outdated. It
must describe the already-wired startup import, live watcher, accounting, filters,
charts, statistics, Sessions activity, and Windows storage behavior.

At the relevant phases, update:

- requirements and installation commands for PySide6;
- supported Python versions so `pyproject.toml`, CI, and README agree;
- development launch commands for Tkinter and Qt during transition;
- default launch command after cutover;
- project structure with `replay/` and `ui_qt/`;
- reviewer usage and keyboard navigation;
- known/unknown opponent-card behavior;
- legacy-hand reduced-detail behavior;
- Windows build and troubleshooting notes;
- screenshots only after the Qt visual design is stable.

README acceptance criteria:

- It contains no statement that startup import or live watching is unwired.
- Every documented command is executed in CI or manually verified before release.
- It clearly distinguishes current behavior from planned behavior.
- It never promises reconstruction of data absent from Winamax history.

### 12.2 Changelog

Maintain an `[Unreleased]` section during development. Update it in every phase with
user-visible or migration-relevant changes.

Required entries include:

- enriched replay persistence and automatic re-import;
- legacy/incomplete replay behavior;
- hand reviewer and navigation;
- known-opponent-card privacy control;
- Qt beta availability;
- Qt becoming the default UI;
- installer or system-requirement changes;
- Tkinter fallback and eventual removal.

Do not rewrite released `0.6.0` notes. Move `[Unreleased]` content into a dated release
only when the version in `pyproject.toml` is updated and release validation passes.

### 12.3 Supporting documents

Create and maintain:

- `docs/replay-data-contract.md`: field semantics and amount conventions;
- `docs/replay-validation.md`: fixture-by-fixture expected states;
- `docs/qt-architecture.md`: controller, service, threading, and UI boundaries;
- a short migration note for any release that changes stored replay data.

## 13. Performance Requirements

- Session and hand lists must be paginated; default page size should be 50-100.
- Loading a reviewer may query one hand and nearby navigation IDs, not all hands.
- Replay states may be cached per open hand but are not stored in SQLite.
- UI filtering must use repository queries and existing indexes.
- Import and replay parsing must not run on the UI thread.
- A session with thousands of hands must remain navigable without constructing one
  widget per hand at application startup.
- Performance checks must include a synthetic database with at least 100,000 hands.

## 14. Security, Privacy, and Correctness

- All analysis remains local.
- Do not send hand histories or player names to external services.
- Do not interact with the Winamax process or provide live decision support.
- Do not reveal opponent cards unless they are explicitly present in source history.
- Treat malformed source as data-quality information, not permission to guess.
- Escape player names and source text when rendering rich text.
- Preserve original imported facts separately from derived replay state.

## 15. Risks and Controls

| Risk | Control |
| --- | --- |
| Qt packaging misses plugins | Windows packaging spike before UI work |
| Big-bang rewrite regresses accounting | Incremental screens and parity matrix |
| Existing DB loses data | Additive migrations and snapshot upgrade tests |
| Re-import overwrites manual corrections | Explicit regression tests |
| Replay pot math is subtly wrong | Pure engine, action fixtures, reconciliation |
| Missing source creates fake certainty | Completeness flag and `Unknown` UI |
| UI thread freezes during import | Worker execution with Qt signal boundary |
| Installer becomes unexpectedly large | Record size during Phase 0 and each release |
| README drifts again | Documentation acceptance gate in each phase |

## 16. Out of Scope

- Separate reviewer repository or Git submodule.
- Real-time HUD, Winamax automation, or live advice.
- Equity, range, hand-strength, leak, or opponent analysis.
- Invented opponent cards or inferred hidden actions.
- Cloud accounts or synchronization.
- Dark mode before core feature parity.
- Removing Tkinter before a stable Qt release.

## 17. Final Acceptance Criteria

The hand-reviewer and Qt migration project is complete only when all statements below
are true.

### Data and compatibility

- [ ] Existing supported databases upgrade in place with no loss of hands,
  tournaments, sessions, accounting events, or manual entry corrections.
- [ ] Available source files can enrich existing hands without duplicate records.
- [ ] Legacy hands without enriched data open in an explicitly reduced-detail mode.
- [ ] Replay facts are loaded from structured persistence, not parsed inside the UI.
- [ ] Unknown data remains unknown and opponent cards are never invented.

### Reviewer correctness

- [ ] Cash, tournament, and Expresso sessions open ordered hand lists.
- [ ] First/previous/next/last hand navigation works without leaving the reviewer.
- [ ] Previous/next/restart/play action controls work deterministically.
- [ ] Players, seats, dealer, stacks, blinds, antes, actions, board, pot, and result
  match validated source fixtures.
- [ ] Known opponent cards respect the visibility toggle.
- [ ] Unknown opponent cards display `??`.
- [ ] All-ins, folds, showdowns, uncalled returns, side pots, and split pots have
  deterministic tests.
- [ ] Textual action history remains available beside the visual replay.
- [ ] Hand and graph entry points retain and open the exact stable hand ID.

### Existing-feature parity

- [ ] Every row in the feature-parity matrix passes in source and packaged Windows
  builds.
- [ ] EUR accounting, BB metrics, ROI, rake, free entries, re-entries, and UTC policy
  produce the same validated results as before migration.
- [ ] Startup import, live watcher refresh, settings, logging, and clean shutdown work.
- [ ] Global mode/date filters affect dashboard, statistics, sessions, hands, and
  charts consistently.
- [ ] Large chart histories retain zoom boundaries, extrema, and source links.

### UI and delivery

- [ ] Qt is the default packaged UI and no normal workflow requires Tkinter.
- [ ] The application is usable at required resolutions and Windows scale factors
  without clipping, overlap, or unreadable text.
- [ ] Keyboard navigation and visible focus work for history and replay controls.
- [ ] Linux CI, Windows CI, full pytest, Ruff, mypy, Qt smoke, packaged launch, and
  installer upgrade checks pass.
- [ ] MyPokerTracker name, icon, paths, version metadata, and retained user data are
  unchanged unless explicitly documented.
- [ ] README, changelog, replay contract, Qt architecture, and migration notes match
  the released application.

## 18. First Implementation Slice

Start with Phase 0 and Phase 1 only:

1. Correct the README's current-state inventory.
2. Record the Qt dependency/packaging decision and prove a minimal packaged window.
3. Define `ReplayHand`, `ReplayPlayer`, and `ReplayAction` without changing the UI.
4. Add parser fixture tests for seats, stacks, dealer, forced bets, shown cards,
   uncalled returns, and exact action order.
5. Do not begin the visual poker table until those tests define a reliable replay
   source contract.