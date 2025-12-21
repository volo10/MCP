# MCP League System

A multi-agent league system implementing the MCP (Model Context Protocol) for AI agent communication.

## Overview

This project implements a complete league system where AI agents compete in an Even/Odd game tournament using the `league.v2` protocol over JSON-RPC 2.0.

### Components

| Component | Port | Description |
|-----------|------|-------------|
| League Manager | 8000 | Central orchestrator - handles registration, scheduling, standings |
| Referee REF01 | 8001 | Match manager - runs games, determines winners |
| Referee REF02 | 8002 | Match manager (backup) |
| Player P01 | 8101 | Game participant with random strategy |
| Player P02 | 8102 | Game participant with history-based strategy |
| Player P03 | 8103 | Game participant with adaptive strategy |
| Player P04 | 8104 | Game participant with random strategy |

## Project Structure

```
L07/
├── run_league.py              # Startup script
├── test_system.py             # Integration tests
├── SHARED/
│   ├── config/                # Configuration files
│   ├── data/                  # Runtime data (standings, matches)
│   ├── logs/                  # JSONL logs
│   └── league_sdk/            # Python SDK
└── agents/
    ├── league_manager/        # League Manager agent
    ├── referee_REF01/         # Referee agents
    ├── referee_REF02/
    ├── player_P01/            # Player agents
    ├── player_P02/
    ├── player_P03/
    └── player_P04/
```

## Installation

```bash
# Install dependencies
pip install fastapi uvicorn httpx

# Run integration tests
python test_system.py
```

## Quick Start

```bash
# Start the entire league system
python run_league.py --interactive

# In interactive mode:
league> start      # Create Round-Robin schedule
league> round      # Run next round
league> standings  # View current standings
league> stop       # Shutdown all agents
```

## Protocol

All agents communicate using:
- **Protocol Version**: `league.v2`
- **Transport**: JSON-RPC 2.0 over HTTP
- **Message Format**: Envelope with `protocol`, `message_type`, `sender`, `timestamp` (UTC)
- **Authentication**: `auth_token` assigned during registration

### Message Flow

```
1. Startup:
   League Manager → Ready
   Referees → REFEREE_REGISTER_REQUEST → League Manager
   Players → LEAGUE_REGISTER_REQUEST → League Manager

2. Match Flow:
   League Manager → ROUND_ANNOUNCEMENT → All Players
   Referee → GAME_INVITATION → Players
   Players → GAME_JOIN_ACK → Referee
   Referee → CHOOSE_PARITY_CALL → Players
   Players → CHOOSE_PARITY_RESPONSE → Referee
   Referee → GAME_OVER → Players
   Referee → MATCH_RESULT_REPORT → League Manager

3. Round End:
   League Manager → LEAGUE_STANDINGS_UPDATE → All Players
```

## Game Rules (Even/Odd)

1. Two players each choose "even" or "odd"
2. Referee draws a random number (1-10)
3. If number is even → "even" choosers win
4. If number is odd → "odd" choosers win
5. If both correct/wrong → Draw

**Scoring**: Win = 3 pts, Draw = 1 pt, Loss = 0 pts

## SDK Components

### league_sdk

- `config_models.py` - Dataclasses for configuration
- `config_loader.py` - Lazy-loading ConfigLoader
- `repositories.py` - StandingsRepository, MatchRepository, PlayerHistoryRepository
- `logger.py` - JsonLogger for JSONL format

### Player Strategies

- **Random**: 50/50 choice
- **History**: Analyzes past wins
- **Adaptive**: Tracks opponent patterns

### Resilience

- Exponential backoff retry
- Circuit breaker pattern
- Timeout handling (E001)
- Connection error handling (E009)

## API Endpoints

### League Manager (Port 8000)
```
POST /mcp
  - register_referee
  - register_player
  - start_league
  - announce_round
  - report_match_result
  - league_query

GET /health
GET /standings
```

### Referee (Ports 8001-8002)
```
POST /mcp
  - notify (ROUND_ANNOUNCEMENT)
  - run_match
  - get_match_state

GET /health
```

### Player (Ports 8101-8104)
```
POST /mcp
  - game_invitation
  - choose_parity
  - notify_game_over
  - notify
  - get_stats
  - get_history

GET /health
```

## License

Educational project based on "AI Agents with MCP" protocol specification.

