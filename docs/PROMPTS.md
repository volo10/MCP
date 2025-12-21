# Project Prompts Documentation

This document records all the prompts used to create the MCP League System project.

---

## Prompt 1: Project Structure and SDK

**Task**: Create the project structure and shared SDK according to Chapter 11 of the league protocol.

### Requirements Given:

> "Create the project structure and shared SDK according to Chapter 11 of the league protocol.
>
> 1. **Folder Structure**: Create a `SHARED/` directory with `config/`, `data/`, and `logs/` subfolders. Create an `agents/` directory for the 7 agents.
>
> 2. **league_sdk**: In `SHARED/league_sdk/`, implement the following based on Chapter 10:
>    - `config_models.py`: Use Python dataclasses for `SystemConfig`, `PlayerConfig`, `RefereeConfig`, and `LeagueConfig`.
>    - `config_loader.py`: A `ConfigLoader` class with a lazy-loading pattern to read from `SHARED/config/`.
>    - `repositories.py`: Implement `StandingsRepository`, `MatchRepository`, and `PlayerHistoryRepository` using the Repository Pattern.
>    - `logger.py`: A `JsonLogger` class that writes structured logs in JSONL format to `SHARED/logs/`."

### Implementation:

- Created folder structure: `SHARED/{config,data,logs}`, `agents/`
- Implemented `config_models.py` with dataclasses:
  - `SystemConfig`, `NetworkConfig`, `SecurityConfig`, `TimeoutsConfig`
  - `PlayerConfig`, `RefereeConfig`, `LeagueManagerConfig`, `AgentsConfig`
  - `LeagueConfig`, `ScoringConfig`, `ParticipantsConfig`, `ScheduleConfig`
  - `GameTypeConfig`, `GamesRegistry`
- Implemented `config_loader.py` with lazy-loading `ConfigLoader`
- Implemented `repositories.py` with Repository Pattern
- Implemented `logger.py` with `JsonLogger` for JSONL format

---

## Prompt 2: League Manager Agent

**Task**: Implement the League Manager Agent with FastAPI.

### Requirements Given:

> "Implement the League Manager Agent in `agents/league_manager/` using FastAPI as an MCP Server.
>
> 1. **Registration (Ch. 4.1, 4.2)**: Implement `register_referee` and `register_player` tools. The agent must assign unique IDs (P01, REF01) and generate an `auth_token` for each.
>
> 2. **Scheduler (Ch. 3.5, 8.5)**: Implement a Round-Robin algorithm to create a match schedule for 4 players.
>
> 3. **Communication**: Implement `ROUND_ANNOUNCEMENT` to notify players about the schedule.
>
> 4. **Persistence**: Use the `league_sdk` to update `standings.json` whenever a `MATCH_RESULT_REPORT` is received."

### Implementation:

- Created `main.py` with FastAPI MCP server on port 8000
- Created `handlers.py` with:
  - `register_referee` → assigns REF01, REF02, etc.
  - `register_player` → assigns P01, P02, etc.
  - `auth_token` generation using `secrets.token_hex()`
  - `ROUND_ANNOUNCEMENT` broadcasting
  - `MATCH_RESULT_REPORT` handling with standings update
- Created `scheduler.py` with Round-Robin algorithm:
  - For n players: n-1 rounds, n(n-1)/2 total matches
  - Circle rotation method for schedule generation

---

## Prompt 3: Referee Agent

**Task**: Develop the Referee Agent for match management.

### Requirements Given:

> "Develop the Referee Agent in `agents/referee/`.
>
> 1. **Startup**: Upon launch, it must send a `REFEREE_REGISTER_REQUEST` to the League Manager at port 8000.
>
> 2. **Match Flow (Ch. 3.2)**: Implement the sequence:
>    - Send `GAME_INVITATION` to 2 players.
>    - Call `choose_parity` for both via JSON-RPC.
>    - Draw a random number (1-10) and use the `game_logic.py` to determine the winner based on Even/Odd rules.
>
> 3. **Results**: Send `GAME_OVER` to players and `MATCH_RESULT_REPORT` to the League Manager."

### Implementation:

- Created `main.py` with FastAPI server on ports 8001-8002
- Auto-registration with League Manager on startup
- Created `game_logic.py` with `EvenOddGame` class:
  - `validate_choice()` - validates "even"/"odd"
  - `draw_number()` - random 1-10
  - `determine_winner()` - applies game rules
  - `create_technical_loss()` - handles timeouts
- Created `handlers.py` with complete match flow:
  - `GAME_INVITATION` → `GAME_JOIN_ACK`
  - `CHOOSE_PARITY_CALL` → `CHOOSE_PARITY_RESPONSE`
  - `GAME_OVER` to players
  - `MATCH_RESULT_REPORT` to League Manager

---

## Prompt 4: Player Agent

**Task**: Create a Player Agent template with strategies and resilience.

### Requirements Given:

> "Create a Player Agent template in `agents/player/`.
>
> 1. **Registration**: On startup, register with the League Manager to receive a `player_id` and `auth_token`.
>
> 2. **MCP Tools**: Implement `handle_game_invitation`, `choose_parity`, and `notify_match_result`.
>
> 3. **Strategy (Ch. 3.6)**: Implement an autonomous strategy. The agent should choose 'even' or 'odd' (lowercase) based on random choice or historical data from its `history.json`.
>
> 4. **Resilience (Ch. 5.9)**: Implement Retry logic with Exponential Backoff for connection errors and handle Timeouts (E001)."

### Implementation:

- Created `main.py` with FastAPI server on ports 8101-8104
- Auto-registration with League Manager using retry client
- Created `handlers.py` with MCP tools:
  - `handle_game_invitation` → returns `GAME_JOIN_ACK`
  - `handle_choose_parity` → uses strategy, returns choice
  - `handle_game_over` → updates history
- Created `strategy.py` with three strategies:
  - `RandomStrategy` - 50/50 random choice
  - `HistoryBasedStrategy` - analyzes past wins from `history.json`
  - `AdaptiveStrategy` - tracks opponent patterns, recent numbers
- Created `resilience.py` with:
  - `RetryClient` - exponential backoff (delay = initial × 2^attempt)
  - `CircuitBreaker` - CLOSED → OPEN → HALF_OPEN states
  - Error codes: E001 (TIMEOUT), E009 (CONNECTION)

---

## Prompt 5: Startup Script

**Task**: Create a startup script for the full system.

### Requirements Given:

> "Create a startup script (`run_league.py`) to launch the full system as defined in Chapter 8.2:
>
> 1. Start League Manager (Port 8000).
> 2. Start 2 Referees (Ports 8001, 8002).
> 3. Start 4 Players (Ports 8101, 8102, 8103, 8104).
>
> Ensure each agent uses its respective port and ID. All agents must use the shared protocol: `league.v2` and wrap messages in the Envelope format with a valid timestamp and `auth_token`."

### Implementation:

- Created `run_league.py` with `LeagueRunner` class
- Ordered startup: League Manager → Referees → Players
- Health checking with socket connection wait
- Interactive mode with commands:
  - `start` - create Round-Robin schedule
  - `round` - announce and run next round
  - `standings` - show current standings
  - `stop` - graceful shutdown
- Graceful shutdown handling (Ctrl+C)
- Separate log files for each agent

---

## Prompt 6: GitHub Push

**Task**: Push project to GitHub repository.

### Requirements Given:

> "Please push project to this git - https://github.com/volo10/MCP"

### Implementation:

- Initialized git repository
- Created `.gitignore` for Python, logs, data files
- Created `README.md` with project documentation
- Committed 58 files (12,061 lines)
- Pushed to https://github.com/volo10/MCP

---

## Summary

| Prompt | Focus Area | Files Created |
|--------|------------|---------------|
| 1 | Project Structure & SDK | 11 files in `SHARED/` |
| 2 | League Manager | 5 files in `agents/league_manager/` |
| 3 | Referee Agent | 5 files × 2 referees |
| 4 | Player Agent | 6 files × 4 players |
| 5 | Startup Script | `run_league.py`, `test_system.py` |
| 6 | GitHub | `README.md`, `.gitignore` |

**Total**: 58 files, 12,061 lines of code

