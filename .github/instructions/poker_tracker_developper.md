# Poker Tracker Developer Guide

## Project Name

Poker Tracker - Winamax Desktop Application

## Objective

Create a Windows desktop poker tracker application for personal use.

The application will monitor Winamax poker hand history files in real time, parse played hands and tournament information, store the data locally, and provide a dashboard to analyze poker performance.

The goal is to build a lightweight alternative to professional poker trackers, focused on:

* simplicity
* personal statistics
* learning improvement
* real-time tracking
* extensibility

The application must be developed in Python.

---

# Main Technologies

## Programming Language

Python 3.12+

## User Interface

Tkinter

Purpose:

* desktop dashboard
* statistics display
* hand history browsing
* tournament overview

## Database

SQLite

Purpose:

* store tournaments
* store hands
* store player actions
* store statistics

## File Monitoring

Watchdog

Purpose:

Monitor Winamax hand history folder:

```
C:\Users\Quentin Bonopera\AppData\Roaming\winamax\documents
```

Detect new or modified files automatically.

---

# Application Architecture

Project structure:

```
poker_tracker/

│
├── main.py
│
├── config/
│   └── config.json
│
├── database/
│   ├── database.py
│   └── models.py
│
├── watcher/
│   └── file_watcher.py
│
├── parser/
│   ├── hand_parser.py
│   └── tournament_parser.py
│
├── statistics/
│   └── calculator.py
│
├── ui/
│   ├── dashboard.py
│   ├── hands_view.py
│   └── tournaments_view.py
│
├── tests/
│
└── data/
    └── poker_tracker.db

```

---

# Version 1 Goals (MVP)

The first version must:

## 1. Monitor Winamax Files

The application must:

* watch the Winamax documents folder
* detect new hand history files
* detect tournament summary files
* avoid importing the same file twice

---

## 2. Parse Tournament Information

Example input:

```
Winamax Poker - Tournament summary

Tournament started
Prizepool
Registered players
Finished position
```

Extract:

* tournament id
* tournament name
* buy-in
* prize pool
* number of players
* start time
* finish position
* duration

Store in database.

---

## 3. Parse Hand History

Example:

```
Dealt to MyPseudo [Ac Qd]

*** FLOP ***
[6s Js 4s]

*** TURN ***
[3h]

*** RIVER ***
[Ts]

SUMMARY
```

Extract:

* hand id
* tournament id
* date
* table name
* hero player
* hero cards
* board cards
* players
* actions
* pot size
* result
* winner

---

# Database Design

## Tournament Table

Fields:

```
id
tournament_id
name
buy_in
prize_pool
players_count
started_at
finished_at
position
```

---

## Hands Table

Fields:

```
id
hand_id
tournament_id
played_at
table_name
hero
hero_cards
board
pot
result
```

---

## Players Table

Fields:

```
id
name
```

---

## Actions Table

Fields:

```
id
hand_id
player
street
action
amount
```

Example:

```
MyPseudo
PRE_FLOP
CALL
19975
```

---

# User Interface Requirements

The dashboard should display:

## Main screen

Example:

```
Poker Tracker

Today

Hands played: 150
Tournaments: 8
Profit: +12€

------------------

Recent hands

Hand #12345
AQ offsuit
Lost

------------------

Statistics

VPIP
PFR
Win rate

```

---

# Statistics System

Version 1:

Calculate:

## Volume

* hands played
* tournaments played
* total time

## Results

* winnings
* losses
* ROI
* ITM percentage

## Poker statistics

* VPIP
* PFR
* Limp percentage
* Aggression factor
* Showdown win percentage

---

# Development Steps

## Step 1 - Project Setup

Create:

* Python environment
* project structure
* dependencies

Dependencies:

```
watchdog
sqlite3
pytest
tkinter
```

---

## Step 2 - Database Layer

Create:

* database initialization
* tables
* insert functions
* query functions

The database layer must be independent from UI.

---

## Step 3 - File Watcher

Implement:

* Winamax folder monitoring
* new file detection
* event handling

Output:

```
New hand history detected
```

---

## Step 4 - Parser Development

Create parser modules:

```
hand_parser.py
tournament_parser.py
```

Requirements:

* use regular expressions
* handle missing fields
* never crash on invalid files
* return structured Python objects

Example:

```python
{
"hand_id":"12345",
"hero":"MyPseudo",
"cards":"Ac Qd"
}

```

---

## Step 5 - Database Import

Connect:

Watcher

↓

Parser

↓

Database

Flow:

```
New file
   |
Parse
   |
Validate
   |
Save SQLite
```

---

## Step 6 - Build Tkinter Interface

Create:

* dashboard
* hand list
* tournament list
* statistics page

---

## Step 7 - Testing

Create tests for:

* parser
* database
* file watcher

Use real Winamax examples as test files.

---

# AI Development Rules

When generating code:

1. Always respect the existing architecture.

2. Do not create unnecessary files.

3. Keep modules independent.

4. Use type hints.

Example:

```python
def parse_hand(text:str) -> dict:
```

5. Add comments for complex logic.

6. Never hardcode:

* username
* file path
* database location

Use:

```
config.json
```

Example:

```json
{
 "player_name":"MyPseudo",
 "winamax_folder":"C:/Users/.../documents"
}

```

---

# Future Improvements

Possible version 2:

* bankroll graph
* filtering by tournament
* hand replay viewer
* advanced statistics
* export CSV

Possible version 3:

* poker hand evaluator
* equity calculator
* automatic hand review
* leak detection

---

# Additional Recommendations Before Starting

Add these features early:

## 1. Logging System

Create:

```
logs/
```

The application should record:

* imported files
* parser errors
* database errors

## 2. Import History

Create a table:

```
imports
```

Store:

* filename
* date imported
* status

This prevents duplicates.

## 3. Backup System

Automatically backup:

```
poker_tracker.db
```

because the database contains all collected history.

## 4. Configuration File

Never store settings in code.

Use:

```
config.json
```

for:

* player name
* folders
* preferences

---

# Final Goal

The final application should behave like:

1. Winamax creates a hand history file.

2. Poker Tracker detects it instantly.

3. The parser extracts information.

4. Data is stored in SQLite.

5. The dashboard updates automatically.

6. The user can review his poker activity and improve his game using personal statistics.
