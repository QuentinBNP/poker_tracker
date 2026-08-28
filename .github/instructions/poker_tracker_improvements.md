# Poker Tracker — Version 2.0 / 2.5 Development Specification

## 1. Project Context

This project is a Windows desktop poker tracker for Winamax.

Current stack:

* Python
* SQLite
* Tkinter
* Watchdog
* Winamax hand histories and tournament summaries

The MVP already imports poker data and provides a basic dashboard.

The current dashboard is not sufficiently useful for serious analysis.

The objective of versions 2.0 and 2.5 is to transform the application into a useful poker analysis tool.

The application must remain focused on **historical analysis and review**.

It must not interact with Winamax to make decisions or automatically play.

---

# 2. Development Philosophy

Before implementing v2, inspect the existing codebase.

Do NOT rewrite the MVP from scratch.

First identify:

* existing database schema
* existing parsers
* existing models
* existing statistics
* existing Tkinter views
* how hands are currently linked to tournaments
* how cash games and Expresso games are currently represented

Reuse existing functionality wherever possible.

Before changing the database schema, understand how existing imported data can be migrated.

All new features must work with existing MVP data.

---

# 3. Game Modes

The application must distinguish between:

```text
CASH_GAME
TOURNAMENT
EXPRESSO
```

Every relevant hand/session/result must have a game mode.

The mode must be determined from the Winamax data when possible.

Do not rely exclusively on the UI to determine the mode.

---

# 4. Sessions

A new first-class concept should be introduced:

## Session

A session represents a continuous playing period at a specific table/event.

Examples:

```text
Cash Game
NL2 — Table XYZ
18:32 → 19:47
```

```text
Tournament
Freeroll
14:02 → 16:31
```

```text
Expresso
€1 Expresso
12:41 → 12:47
```

A session should contain:

* session ID
* game mode
* table ID/name when available
* tournament ID when applicable
* start time
* end time
* number of hands
* result
* duration

The exact implementation must be adapted to the existing database.

---

# 5. Bankroll System

The dashboard must have a dedicated bankroll section.

The application must calculate bankroll evolution over time.

## Bankroll graph

Display:

```text
Bankroll
   ^
   |
   |                ______
   |          _____/
   |     ____/
   |____/
   +-----------------------> Time
```

The graph must be interactive.

The user should be able to:

* zoom
* move across the graph
* hover over points
* see date/time
* see bankroll at that point
* see the associated session/tournament when possible

---

# 6. Bankroll Filters

The bankroll graph must support:

```text
All
Cash Game
Tournament
Expresso
```

The user must be able to compare:

### Total

All game modes combined.

### Cash Game

Cash results only.

### Tournament

Tournament results only.

### Expresso

Expresso results only.

The graph must never mix incompatible metrics without clearly explaining what is being displayed.

---

# 7. Financial Metrics

For every mode calculate at minimum:

## Cash Game

* total hands
* total profit
* total buy-in/session investment where applicable
* BB won/lost
* BB/100
* win rate
* number of sessions
* average session result
* best session
* worst session
* total playing time
* hourly rate

## Tournament

* tournaments played
* total buy-ins
* total winnings
* net profit
* ROI
* ITM %
* average finish
* median finish
* best finish
* number of wins
* total playing time
* hourly rate

## Expresso

* games played
* total buy-ins
* total winnings
* net profit
* ROI
* average result
* number of wins
* total playing time

---

# 8. Important Metric Rule

Do not treat all poker modes identically.

For example:

```text
BB/100
```

is meaningful for cash games.

It should not automatically be presented as the primary performance metric for tournaments.

Similarly:

```text
ROI
```

is highly relevant for tournaments and Expresso but is not the main cash-game metric.

The UI must display metrics appropriate to the selected mode.

---

# 9. Dashboard Redesign

The current dashboard should be replaced by a more useful analytics dashboard.

Suggested structure:

```text
+------------------------------------------------------+
| Poker Tracker                                        |
+------------------------------------------------------+

Game mode:
[ ALL ] [ CASH ] [ TOURNAMENT ] [ EXPRESSO ]

Period:
[ Start date ] [ End date ]

--------------------------------------------------------

BANKROLL

                Bankroll graph
              /---------------

--------------------------------------------------------

PERFORMANCE

Hands / Games       Profit       ROI       Win rate
12,482              +€42.31      18.4%     +3.2 BB/100

--------------------------------------------------------

POKER STATS

VPIP       PFR       3-Bet       WTSD       W$SD
24.1%      19.8%     7.2%        27.4%      51.2%

--------------------------------------------------------

RECENT SESSIONS

Date        Mode          Duration    Hands     Result
...

--------------------------------------------------------

RECENT HANDS

Hand #...   AQo    BTN    +12 BB
Hand #...   77     CO     -8 BB
...
```

The exact UI can differ, but the information hierarchy should remain.

---

# 10. Global Filters

Filters must be available globally where relevant.

Minimum filters:

## Date

```text
Today
Last 7 days
Last 30 days
This month
This year
Custom
All time
```

## Game mode

```text
All
Cash Game
Tournament
Expresso
```

The selected filters must affect:

* bankroll
* statistics
* sessions
* hand lists
* charts

Do not implement separate incompatible filter logic for every screen.

Create a shared filtering layer.

---

# 11. Advanced Statistics

Create a dedicated statistics page.

It must support different statistics depending on game mode.

## Cash Game

At minimum:

* Hands
* VPIP
* PFR
* 3-Bet
* Fold to 3-Bet
* 4-Bet
* Fold to 4-Bet
* Attempt to Steal
* Fold to Steal
* C-Bet Flop
* Fold to C-Bet
* C-Bet Turn
* C-Bet River
* WTSD
* W$SD
* Aggression Frequency
* Aggression Factor
* BB won
* BB/100

## General

Also calculate:

* hands won
* hands lost
* showdown hands
* non-showdown hands
* all-in hands
* all-in win rate

Only show a statistic when enough underlying data exists.

Do not display misleading statistics based on tiny samples.

---

# 12. BB Won/Lost Per Hand

This is a major feature.

For every cash-game hand, calculate:

```text
BB result
```

Example:

```text
Hand 1: +3.5 BB
Hand 2: -2 BB
Hand 3: +18 BB
Hand 4: -1 BB
```

The calculation must use the big blind applicable to that hand.

Do not assume the same big blind for an entire database.

Store or derive:

```text
big_blind
result_chips
result_bb
```

for each hand when possible.

---

# 13. BB W/L Interactive Graph

Create a dedicated graph showing the evolution of BB won/lost.

Example:

```text
BB
 ^
 |                    /
 |          /\_______/
 |     ____/
 |____/
 |
 +------------------------> Hands
```

The graph must be interactive.

The user should be able to:

* zoom
* pan
* hover over a hand
* see the hand number
* see date/time
* see BB result
* see pot size
* see hero cards
* see position
* open the selected hand in the hand viewer

---

# 14. Every Hand Must Be Accessible From The Graph

This is important.

The graph must not only display aggregated data.

Every data point corresponds to a real hand.

When clicking a point:

```text
Hand #4810910666317627480

AQo
BTN
+12.4 BB

Open hand
```

Clicking "Open hand" should open the future hand replay viewer.

The architecture should therefore allow:

```text
Graph
   ↓
Hand ID
   ↓
Hand details
   ↓
Hand replay
```

Do not implement the graph using data that loses the original hand ID.

---

# 15. Tournament History

Create a dedicated Tournament History page.

Display:

```text
Date
Tournament
Buy-in
Prize Pool
Players
Position
Result
ROI
Duration
```

Example:

```text
28/06/2026
Freeroll
€0
€100
3004 players
2892
€0
-
3m38
```

---

# 16. Tournament Filters

Allow filtering by:

### Date

```text
Today
Last 7 days
Last 30 days
Custom
All time
```

### Result

Examples:

```text
All
Won
Final table
ITM
Lost
```

### Ranking

Allow queries such as:

```text
Position <= 10
Position <= 100
Position > 1000
```

or equivalent UI filters.

### Buy-in

Allow filtering by buy-in.

### Tournament name

Allow text search.

---

# 17. Cash Game History

Create a dedicated Cash Game History page.

Display sessions rather than tournaments.

Example:

```text
Date
Table
Stakes
Duration
Hands
Profit
BB
BB/100
```

Filters:

* date
* table
* stakes
* result
* minimum/maximum profit

The user must be able to open a session and see all hands played during that session.

---

# 18. Expresso History

Create a dedicated Expresso History page.

Display:

```text
Date
Buy-in
Prize multiplier when available
Result
Profit
Duration
Hands
```

Allow filtering by:

* date
* buy-in
* result
* multiplier when available

---

# 19. Version 2.5 — Hand Replay Viewer

The hand replay viewer is one of the main features of v2.5.

The goal is to reproduce the useful parts of the Winamax hand history experience using locally stored hand histories.

---

# 20. Session Browser

The user should first select a session.

Possible session types:

```text
Cash Game table
Tournament
Expresso
```

Example:

```text
History

28/06/2026
Freeroll
Tournament
Hands: 42

27/06/2026
NL2 Table #123
Cash Game
Hands: 137

26/06/2026
Expresso €1
Hands: 6
```

Clicking a session opens its hand list.

---

# 21. Session Hand List

Display:

```text
Hand #1
Hand #2
Hand #3
...
Hand #42
```

Each hand should display useful information:

```text
Hand #12
AQo
BTN
Pot: 12.5 BB
Result: +18.2 BB
```

The user can click any hand.

---

# 22. Hand Navigation

The replay viewer must support:

```text
First hand
Previous hand
Next hand
Last hand
```

Keyboard shortcuts are desirable:

```text
← Previous
→ Next
Home First
End Last
```

The user should be able to navigate from:

```text
Hand 1 → Hand 2 → Hand 3 → ... → Last hand
```

without returning to the history screen.

---

# 23. Replay Viewer Layout

The viewer should visually resemble a poker table.

Suggested layout:

```text
                    PLAYER 1
                  20 BB

        PLAYER 2                 PLAYER 3

                 ┌─────────┐
                 │ FLOP    │
                 │ 6s Js 4s│
                 └─────────┘

             HERO
           Ac Qd
           100 BB

              POT: 42 BB
```

The exact visual design can differ.

The important requirement is that the viewer clearly represents:

* players
* positions
* stacks
* dealer button
* blinds
* hero cards
* community cards
* actions
* pot
* current street
* result

---

# 24. Street Navigation

The viewer should reconstruct the hand sequentially:

```text
Pre-Flop
    ↓
Flop
    ↓
Turn
    ↓
River
    ↓
Showdown
```

The user should be able to step through the action.

Example:

```text
[ Previous Action ] [ Play ] [ Next Action ]
```

Optional later feature:

```text
Auto-play
Speed: 0.5x / 1x / 2x
```

Do not prioritize animation over correctness.

---

# 25. Opponent Cards

The viewer must support showing or hiding opponent hole cards.

Example control:

```text
☑ Show known opponent cards
```

If opponent cards are present in the Winamax hand history:

```text
Opponent
Ad 6d
```

the viewer may display them.

If the hand history does not contain the cards:

```text
??
```

must be displayed instead.

The application must never invent opponent cards.

---

# 26. Opponent Card Privacy Logic

Distinguish between:

### Known cards

Cards explicitly available in the imported hand history.

Display them.

### Unknown cards

Cards not present in the hand history.

Display:

```text
??
```

### Folded player

If Winamax does not provide their cards, do not attempt to reconstruct them.

This distinction is essential for a correct replay viewer.

---

# 27. Hand Replay Information

The replay must display:

## Pre-flop

* blinds
* antes
* positions
* stacks
* hole cards when known
* actions
* bet amounts

## Flop

* flop cards
* actions
* pot

## Turn

* turn card
* actions
* pot

## River

* river card
* actions
* pot

## Showdown

* revealed cards
* hand ranking
* winner
* final pot

---

# 28. Hand Detail Panel

Alongside the visual replay, provide a textual action history.

Example:

```text
PRE-FLOP

PikPoPo folds
Allan07 calls 200
Fluo.Tigre27 raises 19,775
MyPseudo calls 19,775
WinnerThePoH folds
...

FLOP
6s Js 4s

TURN
3h

RIVER
Ts
```

This makes debugging the parser and validating the replay much easier.

---

# 29. Search System

The application must have a unified history/search system.

Search by:

* date
* game mode
* tournament
* table
* hand ID
* result
* player
* stakes
* buy-in

The search system should return links to:

```text
Tournament
Session
Hand
```

---

# 30. Data Model Changes

Before implementation, review the current database.

The data model must support relationships similar to:

```text
Tournament
    |
    +---- Session
             |
             +---- Hand
                    |
                    +---- Players
                    |
                    +---- Actions
```

For cash games:

```text
Cash Session
    |
    +---- Hand
    +---- Hand
    +---- Hand
```

For Expresso:

```text
Expresso Session
    |
    +---- Hand
    +---- Hand
```

Do not duplicate hand information unnecessarily.

Use IDs and foreign keys.

---

# 31. Important Database Requirements

Add database indexes for fields frequently searched:

* played_at
* hand_id
* tournament_id
* session_id
* game_mode
* table_name

History searches must remain fast when the database contains hundreds of thousands of hands.

---

# 32. Migration Strategy

If the current MVP schema changes:

Do not delete the existing database.

Create a migration system.

Example:

```text
migration_001
migration_002
migration_003
```

The application must be able to upgrade an existing MVP database to the v2 schema.

---

# 33. Parser Requirements

Do not make the replay viewer dependent on fragile UI parsing.

The parser must produce a structured representation of every hand.

For example:

```python
Hand(
    hand_id=...,
    game_mode=...,
    timestamp=...,
    table=...,
    players=[...],
    hero=...,
    streets=[
        Preflop(...),
        Flop(...),
        Turn(...),
        River(...)
    ],
    result=...
)
```

The exact implementation should follow the existing project's architecture.

The replay viewer should consume this structured representation.

It should NOT parse raw Winamax text itself.

---

# 34. Testing Requirements

Every major feature needs automated tests.

## Parser tests

Test:

* cash game
* tournament
* Expresso
* all-in
* fold
* showdown
* no showdown
* multiple players
* missing opponent cards
* malformed input

## Database tests

Test:

* insertion
* querying
* filtering
* sessions
* migrations
* indexes

## Statistics tests

Test known datasets.

For example:

```text
10 hands
+10 BB
-5 BB
+2 BB
...
```

Verify exact:

```text
Total BB
BB/100
Win rate
```

## Replay tests

Given a known hand history, verify that:

* players are correct
* actions are ordered
* streets are correct
* cards are correct
* pot sizes are correct
* winner is correct

---

# 35. UI Architecture

Do not put SQL queries directly inside Tkinter widgets.

Use a layered architecture:

```text
Tkinter UI
     |
     v
Application / Service Layer
     |
     v
Statistics / History / Replay Services
     |
     v
Repositories
     |
     v
SQLite
```

Example:

```text
Dashboard
    ↓
StatisticsService
    ↓
HandRepository
    ↓
SQLite
```

This will make v2.5 significantly easier to implement.

---

# 36. Performance

The application may eventually contain a very large number of hands.

Do not load every hand into memory when displaying a history page.

Use:

* SQL filtering
* pagination
* indexes
* aggregation queries

For example:

```text
50 hands per page
```

rather than loading 500,000 hands into Tkinter.

---

# 37. Version 2.0 Implementation Order

Implement in this exact general order.

### Phase 1

Review existing architecture and database.

Document:

* current schema
* current parser
* current statistics
* missing information

Do not modify code yet.

### Phase 2

Implement:

* game mode classification
* session model
* database migrations

### Phase 3

Implement shared filtering:

* date
* mode
* table
* tournament

### Phase 4

Implement statistics service.

Separate statistics calculation from UI.

### Phase 5

Implement bankroll calculations.

### Phase 6

Implement new dashboard.

### Phase 7

Implement bankroll graph.

### Phase 8

Implement advanced statistics.

### Phase 9

Implement BB W/L per hand.

### Phase 10

Implement interactive BB graph.

### Phase 11

Add tests and validate all calculations against manually verified examples.

---

# 38. Version 2.5 Implementation Order

### Phase 1

Implement session history.

### Phase 2

Implement tournament history.

### Phase 3

Implement cash-game history.

### Phase 4

Implement Expresso history.

### Phase 5

Implement global search/filtering.

### Phase 6

Implement hand detail view.

### Phase 7

Implement structured replay model.

### Phase 8

Implement poker-table replay UI.

### Phase 9

Implement:

* previous hand
* next hand
* first hand
* last hand

### Phase 10

Implement action-by-action replay.

### Phase 11

Implement opponent card visibility.

### Phase 12

Connect:

```text
Statistics graph
      ↓
Hand
      ↓
Replay viewer
```

---

# 39. AI Coding Rules

The AI developer must follow these rules.

## Rule 1

Do not rewrite working MVP functionality without a concrete reason.

## Rule 2

Before implementing a feature, inspect the current codebase and identify where it belongs.

## Rule 3

Do not put business logic inside Tkinter widgets.

## Rule 4

Do not put SQL queries directly inside UI components.

## Rule 5

All statistics calculations must be testable independently from the UI.

## Rule 6

All statistics must have deterministic tests.

## Rule 7

Never invent poker data.

If information does not exist in the Winamax hand history:

```text
Unknown
```

must be used.

## Rule 8

Never silently guess opponent cards.

## Rule 9

Preserve original Winamax data when possible.

## Rule 10

Do not make assumptions about the big blind.

Read it from the hand data.

## Rule 11

Every hand must have a stable unique identifier.

## Rule 12

Every graph point representing a hand must retain its hand ID.

## Rule 13

Avoid premature optimization, but use database indexes and pagination for large datasets.

## Rule 14

Every new feature must include tests.

---

# 40. Definition of Done — Version 2.0

Version 2.0 is complete when:

* [ ] Dashboard has been redesigned
* [ ] Cash / Tournament / Expresso modes are separated
* [ ] All-mode statistics are available
* [ ] Date filtering works
* [ ] Bankroll graph works
* [ ] Bankroll can be filtered by game mode
* [ ] Cash-game BB/100 is calculated
* [ ] Tournament ROI is calculated
* [ ] Expresso ROI is calculated
* [ ] Advanced poker statistics are available
* [ ] BB won/lost is calculated per hand
* [ ] Interactive BB graph works
* [ ] Clicking a graph hand identifies the hand
* [ ] Existing MVP data remains usable
* [ ] Database migrations exist
* [ ] Statistics have automated tests

---

# 41. Definition of Done — Version 2.5

Version 2.5 is complete when:

* [ ] Session history exists
* [ ] Tournament history exists
* [ ] Cash-game history exists
* [ ] Expresso history exists
* [ ] Date search works
* [ ] Ranking filters work for tournaments
* [ ] Result filters work
* [ ] Buy-in filters work
* [ ] Table/session filtering works
* [ ] Individual hands can be opened
* [ ] Sessions contain ordered hands
* [ ] Hand 1 → last hand navigation works
* [ ] Previous/next hand works
* [ ] Replay viewer displays table state
* [ ] Replay viewer displays actions
* [ ] Replay viewer displays streets
* [ ] Replay viewer displays pot
* [ ] Replay viewer displays hero cards
* [ ] Known opponent cards can be displayed
* [ ] Unknown opponent cards remain hidden
* [ ] Action-by-action replay works
* [ ] Graphs can open the corresponding hand replay
* [ ] Replay data is validated against original Winamax histories

---

# 42. Important Future Features — Do Not Implement Yet

Potential v3+ features:

* hand strength analysis
* equity calculation
* range analysis
* positional analysis
* leak detection
* opponent statistics
* automatic hand categorization
* all-in EV graph
* expected value analysis
* session recommendations
* study/review notes
* tagging hands
* custom hand collections

Do not implement these before v2.0 and v2.5 are stable.

The priority is:

```text
Reliable data
      ↓
Correct statistics
      ↓
Useful dashboard
      ↓
Searchable history
      ↓
Accurate replay
      ↓
Advanced poker analysis
```

---

# 43. Final Product Vision

The final v2 application should allow the user to answer questions such as:

### Overall

> How am I performing overall?

### Cash Game

> Am I winning at cash games?

> What is my BB/100?

> How much money have I won?

> What are my VPIP/PFR/3-Bet statistics?

### Tournament

> How many tournaments have I played?

> What is my ROI?

> How often do I reach the money?

> How many times have I won?

### Expresso

> Am I profitable in Expresso?

> What is my ROI?

### Bankroll

> How has my bankroll evolved?

> Which mode is responsible for my profits?

### Hand Analysis

> Which hands caused my biggest losses?

> What happened in hand #12345?

### Review

> Show me every hand from my session yesterday.

> Let me replay the session from hand 1 to the last hand.

> Show me the opponent cards that are actually known.

This is the target user experience for versions 2.0 and 2.5.
