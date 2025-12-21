# MCP League Protocol Specification

## Protocol Version: league.v2

---

## 1. Overview

The MCP (Model Context Protocol) League Protocol enables AI agents to participate in competitive game leagues. This document specifies the message formats, communication patterns, and rules for the `league.v2` protocol.

### 1.1 Key Principles

1. **Structured Messages**: All messages use JSON objects with defined schemas
2. **JSON-RPC 2.0**: All communication uses JSON-RPC 2.0 over HTTP
3. **UTC Timestamps**: All times in ISO 8601 format with `Z` suffix
4. **Authentication**: `auth_token` required after registration
5. **Envelope Format**: All messages wrapped in standard envelope

---

## 2. Transport Layer

### 2.1 HTTP Endpoints

All agents expose a single MCP endpoint:
```
POST /mcp
Content-Type: application/json
```

### 2.2 Port Assignments

| Agent Type | Port Range | Example |
|------------|------------|---------|
| League Manager | 8000 | http://localhost:8000/mcp |
| Referees | 8001-8010 | http://localhost:8001/mcp |
| Players | 8101-8200 | http://localhost:8101/mcp |

### 2.3 JSON-RPC 2.0 Format

**Request**:
```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": { ... },
  "id": 1
}
```

**Success Response**:
```json
{
  "jsonrpc": "2.0",
  "result": { ... },
  "id": 1
}
```

**Error Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  },
  "id": 1
}
```

---

## 3. Message Envelope

### 3.1 Required Fields

Every protocol message MUST include these fields:

| Field | Type | Description |
|-------|------|-------------|
| `protocol` | string | Must be `"league.v2"` |
| `message_type` | string | Message type identifier |
| `sender` | string | Sender identifier (format: `type:id`) |
| `timestamp` | string | ISO 8601 UTC timestamp with `Z` suffix |

### 3.2 Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | Unique conversation tracker |
| `auth_token` | string | Authentication token (required after registration) |
| `league_id` | string | League identifier |
| `round_id` | integer | Round number |
| `match_id` | string | Match identifier |

### 3.3 Sender Format

```
league_manager          # For League Manager
referee:REF01           # For Referee with ID REF01
player:P01              # For Player with ID P01
```

### 3.4 Timestamp Format

All timestamps MUST be:
- ISO 8601 format
- UTC timezone
- Ending with `Z` suffix

**Valid**:
```
2025-01-15T10:30:00Z
2025-01-15T10:30:00.123Z
```

**Invalid**:
```
2025-01-15T10:30:00+02:00   # Non-UTC timezone
2025-01-15T10:30:00         # Missing Z suffix
```

### 3.5 Example Envelope

```json
{
  "protocol": "league.v2",
  "message_type": "GAME_INVITATION",
  "sender": "referee:REF01",
  "timestamp": "2025-01-15T10:30:00Z",
  "conversation_id": "conv-r1m1-001",
  "auth_token": "tok_abc123def456",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "match_id": "R1M1"
}
```

---

## 4. Registration Messages

### 4.1 REFEREE_REGISTER_REQUEST

**Direction**: Referee → League Manager

```json
{
  "message_type": "REFEREE_REGISTER_REQUEST",
  "referee_meta": {
    "display_name": "Referee Alpha",
    "version": "1.0.0",
    "game_types": ["even_odd"],
    "contact_endpoint": "http://localhost:8001/mcp",
    "max_concurrent_matches": 2
  }
}
```

### 4.2 REFEREE_REGISTER_RESPONSE

**Direction**: League Manager → Referee

```json
{
  "message_type": "REFEREE_REGISTER_RESPONSE",
  "status": "ACCEPTED",
  "referee_id": "REF01",
  "auth_token": "tok_ref01_abc123def456",
  "reason": null
}
```

### 4.3 LEAGUE_REGISTER_REQUEST

**Direction**: Player → League Manager

```json
{
  "message_type": "LEAGUE_REGISTER_REQUEST",
  "player_meta": {
    "display_name": "Agent Alpha",
    "version": "1.0.0",
    "game_types": ["even_odd"],
    "contact_endpoint": "http://localhost:8101/mcp"
  }
}
```

### 4.4 LEAGUE_REGISTER_RESPONSE

**Direction**: League Manager → Player

```json
{
  "message_type": "LEAGUE_REGISTER_RESPONSE",
  "status": "ACCEPTED",
  "player_id": "P01",
  "auth_token": "tok_p01_xyz789abc",
  "reason": null
}
```

---

## 5. Round Messages

### 5.1 ROUND_ANNOUNCEMENT

**Direction**: League Manager → All Players & Referees

```json
{
  "message_type": "ROUND_ANNOUNCEMENT",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "matches": [
    {
      "match_id": "R1M1",
      "game_type": "even_odd",
      "player_A_id": "P01",
      "player_B_id": "P02",
      "referee_id": "REF01",
      "referee_endpoint": "http://localhost:8001/mcp"
    },
    {
      "match_id": "R1M2",
      "game_type": "even_odd",
      "player_A_id": "P03",
      "player_B_id": "P04",
      "referee_id": "REF01",
      "referee_endpoint": "http://localhost:8001/mcp"
    }
  ]
}
```

### 5.2 ROUND_COMPLETED

**Direction**: League Manager → All

```json
{
  "message_type": "ROUND_COMPLETED",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "matches_completed": 2,
  "next_round_id": 2,
  "summary": {
    "total_matches": 2,
    "wins": 1,
    "draws": 1,
    "technical_losses": 0
  }
}
```

---

## 6. Game Messages

### 6.1 GAME_INVITATION

**Direction**: Referee → Player

```json
{
  "message_type": "GAME_INVITATION",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "match_id": "R1M1",
  "game_type": "even_odd",
  "role_in_match": "PLAYER_A",
  "opponent_id": "P02",
  "conversation_id": "conv-r1m1-001"
}
```

### 6.2 GAME_JOIN_ACK

**Direction**: Player → Referee

```json
{
  "message_type": "GAME_JOIN_ACK",
  "match_id": "R1M1",
  "player_id": "P01",
  "arrival_timestamp": "2025-01-15T10:30:00Z",
  "accept": true
}
```

### 6.3 CHOOSE_PARITY_CALL

**Direction**: Referee → Player

```json
{
  "message_type": "CHOOSE_PARITY_CALL",
  "match_id": "R1M1",
  "player_id": "P01",
  "game_type": "even_odd",
  "context": {
    "opponent_id": "P02",
    "round_id": 1,
    "your_standings": {
      "wins": 2,
      "losses": 1,
      "draws": 0
    }
  },
  "deadline": "2025-01-15T10:30:30Z"
}
```

### 6.4 CHOOSE_PARITY_RESPONSE

**Direction**: Player → Referee

```json
{
  "message_type": "CHOOSE_PARITY_RESPONSE",
  "match_id": "R1M1",
  "player_id": "P01",
  "parity_choice": "even"
}
```

**Note**: `parity_choice` MUST be exactly `"even"` or `"odd"` (lowercase).

### 6.5 GAME_OVER

**Direction**: Referee → Both Players

```json
{
  "message_type": "GAME_OVER",
  "match_id": "R1M1",
  "game_type": "even_odd",
  "game_result": {
    "status": "WIN",
    "winner_player_id": "P01",
    "drawn_number": 8,
    "number_parity": "even",
    "choices": {
      "P01": "even",
      "P02": "odd"
    },
    "reason": "P01 chose even, number was 8 (even)"
  }
}
```

**Status Values**:
- `"WIN"` - One player won
- `"DRAW"` - Tie (both correct or both wrong)
- `"TECHNICAL_LOSS"` - Timeout or error

### 6.6 MATCH_RESULT_REPORT

**Direction**: Referee → League Manager

```json
{
  "message_type": "MATCH_RESULT_REPORT",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "match_id": "R1M1",
  "game_type": "even_odd",
  "result": {
    "winner": "P01",
    "score": {
      "P01": 3,
      "P02": 0
    },
    "details": {
      "drawn_number": 8,
      "choices": {
        "P01": "even",
        "P02": "odd"
      }
    }
  }
}
```

---

## 7. Standings Messages

### 7.1 LEAGUE_STANDINGS_UPDATE

**Direction**: League Manager → All Players

```json
{
  "message_type": "LEAGUE_STANDINGS_UPDATE",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "standings": [
    {
      "rank": 1,
      "player_id": "P01",
      "display_name": "Agent Alpha",
      "played": 2,
      "wins": 2,
      "draws": 0,
      "losses": 0,
      "points": 6
    },
    {
      "rank": 2,
      "player_id": "P03",
      "display_name": "Agent Gamma",
      "played": 2,
      "wins": 1,
      "draws": 1,
      "losses": 0,
      "points": 4
    }
  ]
}
```

### 7.2 LEAGUE_COMPLETED

**Direction**: League Manager → All

```json
{
  "message_type": "LEAGUE_COMPLETED",
  "league_id": "league_2025_even_odd",
  "total_rounds": 3,
  "total_matches": 6,
  "champion": {
    "player_id": "P01",
    "display_name": "Agent Alpha",
    "points": 9
  },
  "final_standings": [
    {"rank": 1, "player_id": "P01", "points": 9},
    {"rank": 2, "player_id": "P03", "points": 5},
    {"rank": 3, "player_id": "P02", "points": 3},
    {"rank": 4, "player_id": "P04", "points": 1}
  ]
}
```

---

## 8. Error Messages

### 8.1 LEAGUE_ERROR

**Direction**: League Manager → Requesting Agent

```json
{
  "message_type": "LEAGUE_ERROR",
  "error_code": "E005",
  "error_name": "PLAYER_NOT_REGISTERED",
  "error_description": "Player ID not found in registry",
  "context": {
    "player_id": "P99"
  },
  "retryable": false
}
```

### 8.2 GAME_ERROR

**Direction**: Referee → Player

```json
{
  "message_type": "GAME_ERROR",
  "match_id": "R1M1",
  "player_id": "P01",
  "error_code": "E001",
  "error_name": "TIMEOUT_ERROR",
  "error_description": "Response not received within 30 seconds",
  "game_state": "COLLECTING_CHOICES",
  "retryable": true,
  "retry_count": 1,
  "max_retries": 3
}
```

### 8.3 Error Codes

| Code | Name | Description | Retryable |
|------|------|-------------|-----------|
| E001 | TIMEOUT_ERROR | Response timeout | Yes |
| E003 | MISSING_REQUIRED_FIELD | Required field missing | No |
| E004 | INVALID_PARITY_CHOICE | Invalid choice value | No |
| E005 | PLAYER_NOT_REGISTERED | Unknown player | No |
| E009 | CONNECTION_ERROR | Network failure | Yes |
| E011 | AUTH_TOKEN_MISSING | No token provided | No |
| E012 | AUTH_TOKEN_INVALID | Invalid token | No |
| E018 | PROTOCOL_VERSION_MISMATCH | Wrong protocol version | No |
| E021 | INVALID_TIMESTAMP | Non-UTC timestamp | No |

---

## 9. Timeouts

| Operation | Timeout |
|-----------|---------|
| Referee registration | 10 seconds |
| Player registration | 10 seconds |
| Game join acknowledgment | 5 seconds |
| Parity choice | 30 seconds |
| Match result report | 10 seconds |
| Generic response | 10 seconds |

---

## 10. Retry Policy

For retryable errors (E001, E009):

- **Maximum retries**: 3
- **Backoff strategy**: Exponential
- **Formula**: `delay = initial_delay × 2^attempt`
- **Initial delay**: 1 second
- **Maximum delay**: 30 seconds

After all retries exhausted: **TECHNICAL_LOSS** for non-responding player.

---

## 11. Agent Lifecycle

```
     INIT ────────► REGISTERED ────────► ACTIVE
       │                                    │
       │                                    │
       │            timeout/error           │
       │               ▼                    │
       │           SUSPENDED ◄──────────────┤
       │               │                    │
       │           recover                  │
       │               │                    │
       │               ▼                    │
       │           ACTIVE ◄─────────────────┤
       │                                    │
       └─────────► SHUTDOWN ◄───────────────┘
                (league_end/error)
```

---

## 12. Query Messages

### 12.1 LEAGUE_QUERY

**Direction**: Any → League Manager

```json
{
  "message_type": "LEAGUE_QUERY",
  "query_type": "GET_STANDINGS",
  "league_id": "league_2025_even_odd"
}
```

**Query Types**:
- `GET_STANDINGS` - Current standings
- `GET_SCHEDULE` - Match schedule
- `GET_PLAYERS` - Registered players

---

## Appendix A: Complete Message Type List

| Message Type | Sender | Recipient |
|--------------|--------|-----------|
| REFEREE_REGISTER_REQUEST | Referee | League Manager |
| REFEREE_REGISTER_RESPONSE | League Manager | Referee |
| LEAGUE_REGISTER_REQUEST | Player | League Manager |
| LEAGUE_REGISTER_RESPONSE | League Manager | Player |
| ROUND_ANNOUNCEMENT | League Manager | All |
| ROUND_COMPLETED | League Manager | All |
| GAME_INVITATION | Referee | Player |
| GAME_JOIN_ACK | Player | Referee |
| CHOOSE_PARITY_CALL | Referee | Player |
| CHOOSE_PARITY_RESPONSE | Player | Referee |
| GAME_OVER | Referee | Players |
| MATCH_RESULT_REPORT | Referee | League Manager |
| LEAGUE_STANDINGS_UPDATE | League Manager | All |
| LEAGUE_COMPLETED | League Manager | All |
| LEAGUE_ERROR | League Manager | Agent |
| GAME_ERROR | Referee | Player |
| LEAGUE_QUERY | Any | League Manager |

