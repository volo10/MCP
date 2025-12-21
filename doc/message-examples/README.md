# MCP League Protocol v2 - Message Examples

This directory contains JSON examples for all message types defined in the League Protocol specification.

## Message Categories

### 1. Registration (`registration/`)

| File | Method | Message Type | Description |
|------|--------|--------------|-------------|
| `referee_register_request.json` | `register_referee` | `REFEREE_REGISTER_REQUEST` | Referee registration with League Manager |
| `referee_register_response.json` | (response) | `REFEREE_REGISTER_RESPONSE` | Registration confirmation with referee_id |
| `player_register_request.json` | `register_player` | `LEAGUE_REGISTER_REQUEST` | Player registration with League Manager |
| `player_register_response.json` | (response) | `LEAGUE_REGISTER_RESPONSE` | Registration confirmation with player_id |

### 2. League Flow (`league-flow/`)

| File | Method | Message Type | Description |
|------|--------|--------------|-------------|
| `round_announcement.json` | `notify_round` | `ROUND_ANNOUNCEMENT` | Broadcast new round schedule |

### 3. Configuration (`config/`)

| File | Source | Description |
|------|--------|-------------|
| `system.json` | Ch. 9.3.1 | Global system configuration |
| `league_config.json` | Ch. 9.3.3 | League-specific configuration |
| `game_registry.json` | Ch. 3.8.3 | Supported game types registry |

### 4. Data Files (`data/`)

| File | Source | Description |
|------|--------|-------------|
| `standings.json` | Ch. 9.4.1 | League standings data |
| `player_history.json` | Ch. 9.4.4 | Player match history |

### 5. Log Formats (`logs/`)

| File | Source | Description |
|------|--------|-------------|
| `log_entry.json` | Ch. 9.5.1 | League log file entry format |
| `structured_log_entry.json` | Ch. 5.10.2 | Structured log entry format |

### 6. Game Flow (`game-flow/`)

| File | Method | Message Type | Description |
|------|--------|--------------|-------------|
| `game_invitation.json` | `handle_game_invitation` | `GAME_INVITATION` | Referee invites player to match |
| `game_join_ack.json` | (response) | `GAME_JOIN_ACK` | Player accepts invitation |
| `choose_parity_call.json` | `choose_parity` | `CHOOSE_PARITY_CALL` | Referee requests parity choice |
| `choose_parity_response.json` | (response) | `CHOOSE_PARITY_RESPONSE` | Player's even/odd choice |
| `game_move_call.json` | `game_move` | `GAME_MOVE_CALL` | Generic game move request (Ch. 3.8.2) |
| `game_move_response.json` | (response) | `GAME_MOVE_RESPONSE` | Generic game move response (Ch. 3.8.2) |
| `game_over.json` | `notify_match_result` | `GAME_OVER` | Referee notifies match result |
| `match_result_report.json` | `report_match_result` | `MATCH_RESULT_REPORT` | Referee reports to League Manager |
| `standings_update.json` | `update_standings` | `LEAGUE_STANDINGS_UPDATE` | Updated standings after match |
| `round_completed.json` | `notify_round_completed` | `ROUND_COMPLETED` | Round finished notification |
| `league_completed.json` | `notify_league_completed` | `LEAGUE_COMPLETED` | League finished with champion |

### 4. Errors (`errors/`)

| File | Method | Message Type | Description |
|------|--------|--------------|-------------|
| `league_error.json` | (response) | `LEAGUE_ERROR` | League-level error |
| `game_error.json` | `notify_game_error` | `GAME_ERROR` | Game-level error (timeout, etc.) |

### 5. Queries (`queries/`)

| File | Method | Message Type | Description |
|------|--------|--------------|-------------|
| `league_query.json` | `league_query` | `LEAGUE_QUERY` | Query standings, schedule, etc. |

## Common Envelope Fields

All messages follow the JSON-RPC 2.0 format with a standard envelope:

```json
{
  "jsonrpc": "2.0",
  "method": "method_name",
  "params": {
    "protocol": "league.v2",
    "message_type": "MESSAGE_TYPE",
    "sender": "agent_type:agent_id",
    "timestamp": "2025-01-15T10:00:00Z",
    "conversation_id": "conv-unique-id",
    "auth_token": "tok-xxx-yyy"
  },
  "id": 1
}
```

## Method Name Reference

| Method | Used For |
|--------|----------|
| `register_referee` | Referee registration |
| `register_player` | Player registration |
| `notify_round` | Round announcements |
| `handle_game_invitation` | Game invitations |
| `choose_parity` | Parity choice requests |
| `notify_match_result` | Game over notifications |
| `report_match_result` | Match result reports to League Manager |
| `update_standings` | Standings updates |
| `notify_round_completed` | Round completion |
| `notify_league_completed` | League completion |
| `notify_game_error` | Game errors |
| `league_query` | Query requests |

## ID Numbering Convention

| Range | Purpose |
|-------|---------|
| 1-9 | Registration requests |
| 10-99 | League-level notifications |
| 1001-1099 | Game invitations |
| 1101-1199 | Choose parity calls |
| 1201-1299 | Game over notifications |
| 1301-1399 | Match result reports |
| 1401-1499 | Standings updates |
| 1501-1599 | Queries |
| 2001+ | League completion |

