# MCP League System - Complete Project Documentation

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [The Even/Odd Game](#3-the-evenodd-game)
4. [Agents](#4-agents)
5. [Shared SDK](#5-shared-sdk)
6. [Configuration](#6-configuration)
7. [Data Flow](#7-data-flow)
8. [Message Protocol](#8-message-protocol)
9. [Running the System](#9-running-the-system)
10. [Extending the System](#10-extending-the-system)

---

## 1. Introduction

### 1.1 What is MCP?

MCP (Model Context Protocol) is a communication protocol developed by Anthropic that enables AI agents to communicate with each other. This project implements a league system where multiple agents compete in games using the MCP protocol.

### 1.2 Project Goals

- Demonstrate multi-agent communication using JSON-RPC 2.0
- Implement a complete tournament system with registration, scheduling, and standings
- Show patterns for resilient distributed systems (retry, circuit breaker)
- Provide a template for building agent-based systems

### 1.3 Key Technologies

| Technology | Purpose |
|------------|---------|
| Python 3.10+ | Programming language |
| FastAPI | HTTP server framework |
| JSON-RPC 2.0 | Communication protocol |
| httpx | Async HTTP client |
| Dataclasses | Type-safe configuration |

---

## 2. Architecture Overview

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        League Manager                            │
│                         (Port 8000)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐│
│  │ Registration│ │  Scheduler  │ │    Standings Manager        ││
│  │   Handler   │ │ (Round-Robin│ │  (Update on MATCH_RESULT)   ││
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Referee REF01  │ │  Referee REF02  │ │    (More...)    │
│   (Port 8001)   │ │   (Port 8002)   │ │                 │
│  ┌───────────┐  │ │  ┌───────────┐  │ │                 │
│  │Game Logic │  │ │  │Game Logic │  │ │                 │
│  │(Even/Odd) │  │ │  │(Even/Odd) │  │ │                 │
│  └───────────┘  │ │  └───────────┘  │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │
          └─────────┬─────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌───────┐       ┌───────┐       ┌───────┐
│Player │       │Player │       │Player │
│  P01  │       │  P02  │       │ P03/4 │
│ 8101  │       │ 8102  │       │8103/4 │
└───────┘       └───────┘       └───────┘
```

### 2.2 Directory Structure

```
L07/
├── run_league.py              # Main startup script
├── test_system.py             # Integration tests
├── README.md                  # Project overview
│
├── docs/                      # Documentation
│   ├── PROMPTS.md            # Original prompts
│   ├── PROJECT_DOCUMENTATION.md  # This file
│   └── MCP_PROTOCOL.md       # Protocol specification
│
├── tests/                     # Unit tests
│   ├── test_config_models.py
│   ├── test_config_loader.py
│   ├── test_repositories.py
│   ├── test_logger.py
│   ├── test_game_logic.py
│   └── test_strategy.py
│
├── SHARED/                    # Shared resources
│   ├── config/               # Configuration files
│   │   ├── system.json       # Global settings
│   │   ├── agents/           # Agent registry
│   │   ├── leagues/          # League configs
│   │   ├── games/            # Game type registry
│   │   └── defaults/         # Default values
│   │
│   ├── data/                 # Runtime data
│   │   ├── leagues/          # Standings per league
│   │   ├── matches/          # Match transcripts
│   │   └── players/          # Player history
│   │
│   ├── logs/                 # JSONL logs
│   │   ├── league/           # League-level logs
│   │   ├── agents/           # Per-agent logs
│   │   └── system/           # System logs
│   │
│   └── league_sdk/           # Python SDK
│       ├── __init__.py
│       ├── config_models.py  # Dataclass definitions
│       ├── config_loader.py  # Configuration loading
│       ├── repositories.py   # Data access layer
│       └── logger.py         # Structured logging
│
└── agents/                   # Agent implementations
    ├── league_manager/       # Central orchestrator
    │   ├── main.py          # FastAPI server
    │   ├── handlers.py      # Message handlers
    │   └── scheduler.py     # Round-Robin scheduler
    │
    ├── referee_REF01/        # Match manager
    ├── referee_REF02/
    │   ├── main.py          # FastAPI server
    │   ├── handlers.py      # Match flow handlers
    │   └── game_logic.py    # Even/Odd rules
    │
    ├── player_P01/           # Game participants
    ├── player_P02/
    ├── player_P03/
    └── player_P04/
        ├── main.py          # FastAPI server
        ├── handlers.py      # Game handlers
        ├── strategy.py      # Decision strategies
        └── resilience.py    # Retry/Circuit breaker
```

---

## 3. The Even/Odd Game

### 3.1 Game Rules

The Even/Odd game (יגוז-יא/יגוז) is a simple two-player game:

1. Each player secretly chooses `"even"` or `"odd"`
2. A random number from 1-10 is drawn
3. If the number is even → `"even"` choosers win
4. If the number is odd → `"odd"` choosers win
5. If both chose the same → Draw

### 3.2 Scoring

| Result | Points |
|--------|--------|
| Win | 3 |
| Draw | 1 |
| Loss | 0 |

### 3.3 Why This Game?

- **Simple**: Easy to implement and understand
- **Fair**: 50/50 probability for any strategy
- **Protocol-focused**: Demonstrates communication, not complex AI

### 3.4 Game Logic Implementation

```python
class EvenOddGame:
    def determine_winner(self, player_a, player_b, choice_a, choice_b, drawn_number):
        number_parity = "even" if drawn_number % 2 == 0 else "odd"
        
        a_correct = choice_a == number_parity
        b_correct = choice_b == number_parity
        
        if a_correct and not b_correct:
            return GameResult(status=WIN, winner=player_a, ...)
        elif b_correct and not a_correct:
            return GameResult(status=WIN, winner=player_b, ...)
        else:
            return GameResult(status=DRAW, winner=None, ...)
```

---

## 4. Agents

### 4.1 League Manager

**Purpose**: Central orchestrator for the league.

**Responsibilities**:
- Register referees and players
- Create Round-Robin schedule
- Broadcast round announcements
- Maintain standings

**Port**: 8000

**Key Endpoints**:
```
POST /mcp
  - register_referee    → REFEREE_REGISTER_RESPONSE
  - register_player     → LEAGUE_REGISTER_RESPONSE
  - start_league        → Creates schedule
  - announce_round      → ROUND_ANNOUNCEMENT
  - report_match_result → Updates standings
  - league_query        → GET_STANDINGS, GET_SCHEDULE
```

### 4.2 Referee Agent

**Purpose**: Manages individual matches.

**Responsibilities**:
- Register with League Manager on startup
- Send game invitations to players
- Collect parity choices
- Draw random number and determine winner
- Report results

**Ports**: 8001, 8002

**Match Flow**:
```
1. Receive ROUND_ANNOUNCEMENT
2. For each assigned match:
   a. GAME_INVITATION → Players
   b. Wait for GAME_JOIN_ACK
   c. CHOOSE_PARITY_CALL → Players
   d. Collect CHOOSE_PARITY_RESPONSE
   e. Draw number (1-10)
   f. Determine winner
   g. GAME_OVER → Players
   h. MATCH_RESULT_REPORT → League Manager
```

### 4.3 Player Agent

**Purpose**: Participates in matches.

**Responsibilities**:
- Register with League Manager on startup
- Accept game invitations
- Make parity choices using strategy
- Track match history

**Ports**: 8101-8104

**Strategies**:
| Strategy | Description |
|----------|-------------|
| `random` | 50/50 random choice |
| `history` | Favors historically winning choice |
| `adaptive` | Tracks opponent patterns |

---

## 5. Shared SDK

### 5.1 config_models.py

Dataclass definitions for type-safe configuration:

```python
@dataclass
class SystemConfig:
    schema_version: str
    system_id: str
    protocol_version: str
    network: NetworkConfig
    security: SecurityConfig
    timeouts: TimeoutsConfig
    retry_policy: RetryPolicyConfig
```

### 5.2 config_loader.py

Lazy-loading configuration with caching:

```python
class ConfigLoader:
    def load_system(self) -> SystemConfig:
        if self._system is None:
            self._system = self._parse_system_json()
        return self._system
    
    def load_league(self, league_id: str) -> LeagueConfig:
        if league_id not in self._leagues:
            self._leagues[league_id] = self._parse_league_json(league_id)
        return self._leagues[league_id]
```

### 5.3 repositories.py

Repository pattern for data access:

```python
class StandingsRepository:
    def load(self) -> Dict
    def save(self, standings: Dict) -> None
    def update_player(self, player_id, result, points) -> None

class MatchRepository:
    def create_match(self, match_id, ...) -> Dict
    def set_result(self, match_id, status, winner, details) -> None

class PlayerHistoryRepository:
    def add_match(self, match_id, opponent_id, result, ...) -> None
    def get_matches(self, limit=None) -> List[Dict]
    def get_win_rate(self) -> float
```

### 5.4 logger.py

Structured JSONL logging:

```python
class JsonLogger:
    def log(self, event_type: str, level: str = "INFO", **details):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "component": self.component,
            "event_type": event_type,
            "level": level,
            **details
        }
        # Append to .log.jsonl file
```

---

## 6. Configuration

### 6.1 system.json

Global system settings:

```json
{
  "protocol_version": "league.v2",
  "network": {
    "base_host": "localhost",
    "default_league_manager_port": 8000,
    "default_referee_port_range": [8001, 8010],
    "default_player_port_range": [8101, 8200]
  },
  "timeouts": {
    "move_timeout_sec": 30,
    "generic_response_timeout_sec": 10
  },
  "retry_policy": {
    "max_retries": 3,
    "backoff_strategy": "exponential"
  }
}
```

### 6.2 agents_config.json

Agent registry:

```json
{
  "referees": [
    {"referee_id": "REF01", "endpoint": "http://localhost:8001/mcp", ...}
  ],
  "players": [
    {"player_id": "P01", "default_endpoint": "http://localhost:8101/mcp", ...}
  ]
}
```

### 6.3 league_2025_even_odd.json

League configuration:

```json
{
  "league_id": "league_2025_even_odd",
  "game_type": "even_odd",
  "scoring": {
    "win_points": 3,
    "draw_points": 1,
    "loss_points": 0
  },
  "schedule": {
    "format": "round_robin"
  }
}
```

---

## 7. Data Flow

### 7.1 Registration Phase

```
┌──────────┐    REFEREE_REGISTER_REQUEST    ┌──────────────┐
│ Referee  │ ─────────────────────────────▶ │    League    │
│          │ ◀───────────────────────────── │   Manager    │
└──────────┘    REFEREE_REGISTER_RESPONSE   └──────────────┘
                (referee_id, auth_token)

┌──────────┐    LEAGUE_REGISTER_REQUEST     ┌──────────────┐
│  Player  │ ─────────────────────────────▶ │    League    │
│          │ ◀───────────────────────────── │   Manager    │
└──────────┘    LEAGUE_REGISTER_RESPONSE    └──────────────┘
                (player_id, auth_token)
```

### 7.2 Match Phase

```
League Manager                  Referee                     Players
      │                           │                           │
      │    ROUND_ANNOUNCEMENT     │                           │
      │ ─────────────────────────▶│                           │
      │                           │                           │
      │                           │    GAME_INVITATION        │
      │                           │ ─────────────────────────▶│
      │                           │◀───── GAME_JOIN_ACK ──────│
      │                           │                           │
      │                           │    CHOOSE_PARITY_CALL     │
      │                           │ ─────────────────────────▶│
      │                           │◀─ CHOOSE_PARITY_RESPONSE ─│
      │                           │                           │
      │                           │    [Draw Number 1-10]     │
      │                           │    [Determine Winner]     │
      │                           │                           │
      │                           │      GAME_OVER            │
      │                           │ ─────────────────────────▶│
      │                           │                           │
      │    MATCH_RESULT_REPORT    │                           │
      │◀──────────────────────────│                           │
      │                           │                           │
      │    [Update Standings]     │                           │
      │                           │                           │
      │   LEAGUE_STANDINGS_UPDATE │                           │
      │ ─────────────────────────────────────────────────────▶│
```

---

## 8. Message Protocol

### 8.1 Envelope Format

All messages use this envelope:

```json
{
  "protocol": "league.v2",
  "message_type": "GAME_INVITATION",
  "sender": "referee:REF01",
  "timestamp": "2025-01-15T10:30:00Z",
  "conversation_id": "conv-r1m1-001",
  "auth_token": "tok_abc123...",
  ...
}
```

### 8.2 JSON-RPC 2.0

All HTTP communication uses JSON-RPC 2.0:

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "register_player",
  "params": { ... },
  "id": 1
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "result": { ... },
  "id": 1
}
```

### 8.3 Message Types

| Message Type | Sender | Recipient |
|--------------|--------|-----------|
| REFEREE_REGISTER_REQUEST | Referee | League Manager |
| REFEREE_REGISTER_RESPONSE | League Manager | Referee |
| LEAGUE_REGISTER_REQUEST | Player | League Manager |
| LEAGUE_REGISTER_RESPONSE | League Manager | Player |
| ROUND_ANNOUNCEMENT | League Manager | All |
| GAME_INVITATION | Referee | Player |
| GAME_JOIN_ACK | Player | Referee |
| CHOOSE_PARITY_CALL | Referee | Player |
| CHOOSE_PARITY_RESPONSE | Player | Referee |
| GAME_OVER | Referee | Players |
| MATCH_RESULT_REPORT | Referee | League Manager |
| LEAGUE_STANDINGS_UPDATE | League Manager | All |

---

## 9. Running the System

### 9.1 Prerequisites

```bash
pip install fastapi uvicorn httpx
```

### 9.2 Quick Start

```bash
# Run integration tests
python test_system.py

# Start the league system
python run_league.py --interactive
```

### 9.3 Interactive Commands

```
league> start      # Create Round-Robin schedule
league> round      # Announce and run next round
league> standings  # Show current standings
league> status     # Show agent status
league> stop       # Shutdown all agents
```

### 9.4 Manual Agent Start

```bash
# Terminal 1: League Manager
cd agents/league_manager && python main.py

# Terminal 2: Referee
cd agents/referee_REF01 && python main.py --port 8001

# Terminal 3-6: Players
cd agents/player_P01 && python main.py --port 8101 --strategy random
```

---

## 10. Extending the System

### 10.1 Adding a New Game Type

1. Create game logic module:
```python
# agents/referee_REF01/tic_tac_toe.py
class TicTacToeGame:
    def init_game_state(self, match_id, player_a, player_b): ...
    def validate_move(self, move, board_state): ...
    def make_move(self, player_id, move, state): ...
    def check_winner(self, state): ...
```

2. Register in `games_registry.json`:
```json
{
  "game_type": "tic_tac_toe",
  "move_types": ["place_mark"],
  "valid_choices": {"place_mark": ["0", "1", ..., "8"]}
}
```

### 10.2 Adding a New Strategy

1. Create strategy class:
```python
# agents/player_P01/strategy.py
class MachineLearningStrategy(Strategy):
    def choose(self, context: Dict) -> ParityChoice:
        # Use ML model for prediction
        return self.model.predict(context)
```

2. Register in `StrategyManager`:
```python
STRATEGIES = {
    "random": RandomStrategy,
    "history": HistoryBasedStrategy,
    "ml": MachineLearningStrategy,
}
```

### 10.3 Adding More Players

1. Copy player template:
```bash
cp -r agents/player_P01 agents/player_P05
```

2. Update `agents_config.json`:
```json
{
  "player_id": "P05",
  "default_endpoint": "http://localhost:8105/mcp"
}
```

3. Update `run_league.py`:
```python
self.player_configs.append({
    "name": "Agent Epsilon",
    "port": 8105,
    "strategy": "adaptive"
})
```

---

## Appendix: Error Codes

| Code | Name | Description |
|------|------|-------------|
| E001 | TIMEOUT_ERROR | Response not received in time |
| E003 | MISSING_REQUIRED_FIELD | Required field missing |
| E004 | INVALID_PARITY_CHOICE | Invalid choice (not even/odd) |
| E005 | PLAYER_NOT_REGISTERED | Unknown player ID |
| E009 | CONNECTION_ERROR | Network connection failed |
| E011 | AUTH_TOKEN_MISSING | No auth token provided |
| E012 | AUTH_TOKEN_INVALID | Invalid auth token |

