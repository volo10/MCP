# Architecture Document
## MCP League System

**Version:** 1.0.0
**Last Updated:** 2025-01-15
**Author:** MCP League Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [C4 Model Diagrams](#2-c4-model-diagrams)
3. [Component Details](#3-component-details)
4. [Data Flow](#4-data-flow)
5. [API Contracts](#5-api-contracts)
6. [Architecture Decision Records](#6-architecture-decision-records)
7. [Deployment Architecture](#7-deployment-architecture)
8. [Security Architecture](#8-security-architecture)

---

## 1. Overview

### 1.1 System Purpose

The MCP League System is a distributed multi-agent platform where AI agents compete in game tournaments using the Model Context Protocol (MCP) over JSON-RPC 2.0.

### 1.2 Key Architectural Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Architecture Style** | Distributed Microservices |
| **Communication** | Synchronous HTTP (JSON-RPC 2.0) |
| **Data Storage** | File-based (JSON) |
| **Deployment** | Single-machine, multi-process |

### 1.3 Design Principles

1. **Separation of Concerns**: Each agent has a single responsibility
2. **Loose Coupling**: Agents communicate via well-defined protocols
3. **High Cohesion**: Related functionality grouped together
4. **Resilience**: Fault-tolerant with retry and circuit breaker patterns
5. **Observability**: Comprehensive logging for debugging and analysis

---

## 2. C4 Model Diagrams

### 2.1 Level 1: System Context Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           System Context                                  │
│                                                                          │
│  ┌─────────────────┐                                                     │
│  │   Administrator │                                                     │
│  │     (Person)    │                                                     │
│  └────────┬────────┘                                                     │
│           │ Uses CLI/HTTP                                                │
│           ▼                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │                    MCP League System                               │  │
│  │                                                                    │  │
│  │   A multi-agent tournament platform where AI agents compete       │  │
│  │   in games using the league.v2 protocol over JSON-RPC 2.0        │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│           │                                                              │
│           │ Reads/Writes                                                 │
│           ▼                                                              │
│  ┌─────────────────┐                                                     │
│  │  File System    │                                                     │
│  │ (JSON Storage)  │                                                     │
│  └─────────────────┘                                                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Level 2: Container Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Container Diagram                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        MCP League System                                │ │
│  │                                                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                   League Manager (Port 8000)                     │  │ │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────────────────┐   │  │ │
│  │  │  │ Registration│ │  Scheduler  │ │   Standings Manager      │   │  │ │
│  │  │  │   Handler   │ │ (Round-Robin)│ │   (JSON Persistence)    │   │  │ │
│  │  │  └─────────────┘ └─────────────┘ └──────────────────────────┘   │  │ │
│  │  │                        [FastAPI + Uvicorn]                       │  │ │
│  │  └─────────────────────────────────┬────────────────────────────────┘  │ │
│  │                                    │                                    │ │
│  │              ┌─────────────────────┼─────────────────────┐             │ │
│  │              │                     │                     │             │ │
│  │              ▼                     ▼                     ▼             │ │
│  │  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐    │ │
│  │  │  Referee REF01    │ │  Referee REF02    │ │    (More...)      │    │ │
│  │  │   (Port 8001)     │ │   (Port 8002)     │ │                   │    │ │
│  │  │  ┌─────────────┐  │ │  ┌─────────────┐  │ │                   │    │ │
│  │  │  │ Game Logic  │  │ │  │ Game Logic  │  │ │                   │    │ │
│  │  │  │ (Even/Odd)  │  │ │  │ (Even/Odd)  │  │ │                   │    │ │
│  │  │  └─────────────┘  │ │  └─────────────┘  │ │                   │    │ │
│  │  │    [FastAPI]      │ │    [FastAPI]      │ │                   │    │ │
│  │  └─────────┬─────────┘ └─────────┬─────────┘ └───────────────────┘    │ │
│  │            │                     │                                     │ │
│  │            └──────────┬──────────┘                                     │ │
│  │                       │                                                │ │
│  │     ┌─────────────────┼─────────────────┐                             │ │
│  │     │                 │                 │                             │ │
│  │     ▼                 ▼                 ▼                             │ │
│  │  ┌────────┐       ┌────────┐       ┌────────┐       ┌────────┐       │ │
│  │  │Player  │       │Player  │       │Player  │       │Player  │       │ │
│  │  │  P01   │       │  P02   │       │  P03   │       │  P04   │       │ │
│  │  │ (8101) │       │ (8102) │       │ (8103) │       │ (8104) │       │ │
│  │  │Random  │       │History │       │Adaptive│       │Random  │       │ │
│  │  └────────┘       └────────┘       └────────┘       └────────┘       │ │
│  │    [FastAPI]        [FastAPI]        [FastAPI]        [FastAPI]       │ │
│  │                                                                       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        Shared Resources                              │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │ │
│  │  │   config/   │ │    data/    │ │    logs/    │ │  league_sdk │   │ │
│  │  │   (JSON)    │ │ (Standings) │ │   (JSONL)   │ │  (Python)   │   │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Level 3: Component Diagram (League Manager)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    League Manager - Component Diagram                         │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                         League Manager Agent                           │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                        main.py (FastAPI)                         │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │ │  │
│  │  │  │ POST /mcp   │  │ GET /health │  │ GET /standings          │  │ │  │
│  │  │  │ (JSON-RPC)  │  │             │  │                         │  │ │  │
│  │  │  └──────┬──────┘  └─────────────┘  └────────────┬────────────┘  │ │  │
│  │  │         │                                       │               │ │  │
│  │  └─────────┼───────────────────────────────────────┼───────────────┘ │  │
│  │            │                                       │                  │  │
│  │            ▼                                       │                  │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                     handlers.py                                  │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────┐               │ │  │
│  │  │  │ handle_register_    │  │ handle_register_    │               │ │  │
│  │  │  │     referee()       │  │     player()        │               │ │  │
│  │  │  └─────────────────────┘  └─────────────────────┘               │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────┐               │ │  │
│  │  │  │ handle_start_       │  │ handle_announce_    │               │ │  │
│  │  │  │     league()        │  │     round()         │               │ │  │
│  │  │  └─────────────────────┘  └─────────────────────┘               │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌─────────────────────┐  ┌─────────────────────┐               │ │  │
│  │  │  │ handle_report_      │  │ handle_league_      │               │ │  │
│  │  │  │   match_result()    │  │     query()         │               │ │  │
│  │  │  └─────────────────────┘  └─────────────────────┘               │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │            │                                                          │  │
│  │            ▼                                                          │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                     scheduler.py                                 │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────────┐│ │  │
│  │  │  │ RoundRobinScheduler                                         ││ │  │
│  │  │  │ - generate_schedule(players: List[str]) -> Schedule         ││ │  │
│  │  │  │ - get_round(round_id: int) -> List[Match]                   ││ │  │
│  │  │  └─────────────────────────────────────────────────────────────┘│ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │            │                                                          │  │
│  │            ▼                                                          │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    league_sdk (Shared)                           │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│ │  │
│  │  │  │ConfigLoader │ │ Standings   │ │ JsonLogger  │ │  Parallel   ││ │  │
│  │  │  │             │ │ Repository  │ │             │ │  Utils      ││ │  │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Level 4: Code Diagram (Player Agent Strategy)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Player Agent - Strategy Pattern                            │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        strategy.py                                      │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │                     <<abstract>>                                 │   │  │
│  │  │                       Strategy                                   │   │  │
│  │  │  ─────────────────────────────────────────────────────────────  │   │  │
│  │  │  + choose(context: Dict) -> ParityChoice                        │   │  │
│  │  └───────────────────────────┬─────────────────────────────────────┘   │  │
│  │                              │                                          │  │
│  │          ┌───────────────────┼───────────────────┐                     │  │
│  │          │                   │                   │                     │  │
│  │          ▼                   ▼                   ▼                     │  │
│  │  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐            │  │
│  │  │ RandomStrategy│   │HistoryBased  │   │ AdaptiveStrategy│           │  │
│  │  │               │   │   Strategy   │   │                │            │  │
│  │  │───────────────│   │───────────────│   │────────────────│           │  │
│  │  │+ choose()     │   │- history     │   │- opponent_     │            │  │
│  │  │  50/50 random │   │+ choose()    │   │    patterns    │            │  │
│  │  │               │   │  analyze wins │   │+ choose()      │            │  │
│  │  │               │   │               │   │  detect pattern│            │  │
│  │  └───────────────┘   └───────────────┘   └───────────────┘            │  │
│  │                                                                         │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    StrategyManager                               │   │  │
│  │  │  ─────────────────────────────────────────────────────────────  │   │  │
│  │  │  + get_strategy(name: str) -> Strategy                          │   │  │
│  │  │  + register_strategy(name: str, cls: Type[Strategy])            │   │  │
│  │  │                                                                  │   │  │
│  │  │  STRATEGIES = {                                                  │   │  │
│  │  │      "random": RandomStrategy,                                   │   │  │
│  │  │      "history": HistoryBasedStrategy,                           │   │  │
│  │  │      "adaptive": AdaptiveStrategy,                               │   │  │
│  │  │  }                                                               │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 League Manager

| Attribute | Value |
|-----------|-------|
| **Port** | 8000 |
| **Technology** | FastAPI + Uvicorn |
| **Responsibility** | Central orchestration |

**Key Functions:**
- Register referees and players
- Generate tournament schedule
- Broadcast round announcements
- Maintain standings

### 3.2 Referee Agent

| Attribute | Value |
|-----------|-------|
| **Ports** | 8001-8010 |
| **Technology** | FastAPI + Uvicorn |
| **Responsibility** | Match management |

**Key Functions:**
- Send game invitations
- Collect player choices
- Draw random numbers
- Determine winners
- Report results

### 3.3 Player Agent

| Attribute | Value |
|-----------|-------|
| **Ports** | 8101-8200 |
| **Technology** | FastAPI + Uvicorn |
| **Responsibility** | Game participation |

**Key Functions:**
- Register with league
- Accept game invitations
- Make strategic choices
- Track match history

### 3.4 Shared SDK

| Module | Purpose |
|--------|---------|
| `config_models.py` | Dataclass definitions |
| `config_loader.py` | Configuration management |
| `repositories.py` | Data persistence |
| `logger.py` | Structured logging |
| `parallel.py` | Parallel processing utilities |

---

## 4. Data Flow

### 4.1 Registration Flow

```
┌────────────┐     REFEREE_REGISTER_REQUEST      ┌────────────────┐
│  Referee   │ ──────────────────────────────────▶│ League Manager │
│            │ ◀────────────────────────────────── │                │
└────────────┘     REFEREE_REGISTER_RESPONSE      └────────────────┘
                   (auth_token: "tok_...")

┌────────────┐     LEAGUE_REGISTER_REQUEST       ┌────────────────┐
│  Player    │ ──────────────────────────────────▶│ League Manager │
│            │ ◀────────────────────────────────── │                │
└────────────┘     LEAGUE_REGISTER_RESPONSE       └────────────────┘
                   (auth_token: "tok_...")
```

### 4.2 Match Flow

```
League Manager          Referee               Player A        Player B
      │                    │                     │                │
      │ ROUND_ANNOUNCEMENT │                     │                │
      │───────────────────▶│                     │                │
      │                    │                     │                │
      │                    │   GAME_INVITATION   │                │
      │                    │────────────────────▶│                │
      │                    │────────────────────────────────────▶│
      │                    │                     │                │
      │                    │   GAME_JOIN_ACK     │                │
      │                    │◀────────────────────│                │
      │                    │◀──────────────────────────────────── │
      │                    │                     │                │
      │                    │ CHOOSE_PARITY_CALL  │                │
      │                    │────────────────────▶│                │
      │                    │────────────────────────────────────▶│
      │                    │                     │                │
      │                    │CHOOSE_PARITY_RESPONSE│               │
      │                    │◀────────────────────│                │
      │                    │◀──────────────────────────────────── │
      │                    │                     │                │
      │                    │  [Draw Number]      │                │
      │                    │  [Determine Winner] │                │
      │                    │                     │                │
      │                    │     GAME_OVER       │                │
      │                    │────────────────────▶│                │
      │                    │────────────────────────────────────▶│
      │                    │                     │                │
      │ MATCH_RESULT_REPORT│                     │                │
      │◀───────────────────│                     │                │
      │                    │                     │                │
      │  [Update Standings]│                     │                │
      │                    │                     │                │
```

---

## 5. API Contracts

### 5.1 Message Envelope

All messages use this envelope format:

```json
{
  "protocol": "league.v2",
  "message_type": "GAME_INVITATION",
  "sender": "referee:REF01",
  "timestamp": "2025-01-15T10:30:00Z",
  "auth_token": "tok_abc123...",
  "conversation_id": "conv-r1m1-001",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "match_id": "R1M1"
}
```

### 5.2 JSON-RPC 2.0 Format

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "register_player",
  "params": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_REGISTER_REQUEST",
    "sender": "player:P01",
    "player_id": "P01",
    "display_name": "Agent Alpha",
    "endpoint": "http://localhost:8101/mcp"
  },
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "protocol": "league.v2",
    "message_type": "LEAGUE_REGISTER_RESPONSE",
    "player_id": "P01",
    "auth_token": "tok_abc123def456...",
    "status": "registered"
  },
  "id": 1
}
```

### 5.3 Error Codes

| Code | Name | Description |
|------|------|-------------|
| E001 | TIMEOUT_ERROR | Response timeout |
| E003 | MISSING_REQUIRED_FIELD | Required field missing |
| E004 | INVALID_PARITY_CHOICE | Not "even" or "odd" |
| E005 | PLAYER_NOT_REGISTERED | Unknown player ID |
| E009 | CONNECTION_ERROR | Network failure |
| E011 | AUTH_TOKEN_MISSING | No auth token |
| E012 | AUTH_TOKEN_INVALID | Invalid auth token |

---

## 6. Architecture Decision Records

### ADR-001: JSON-RPC 2.0 over HTTP

**Status:** Accepted

**Context:**
Need a standard protocol for agent-to-agent communication.

**Decision:**
Use JSON-RPC 2.0 over HTTP.

**Rationale:**
- Well-defined standard with clear error handling
- JSON is human-readable and easy to debug
- HTTP is universally supported
- Simpler than gRPC for educational purposes

**Consequences:**
- (+) Easy to understand and implement
- (+) Good tooling support
- (-) Higher overhead than binary protocols
- (-) No streaming support

---

### ADR-002: File-based Persistence

**Status:** Accepted

**Context:**
Need to persist standings and match history.

**Decision:**
Use JSON files for all persistence.

**Rationale:**
- No external database dependency
- Human-readable data
- Simple deployment
- Sufficient for single-machine operation

**Consequences:**
- (+) Zero configuration
- (+) Easy to inspect data
- (-) No concurrent write safety
- (-) Limited scalability

---

### ADR-003: FastAPI Framework

**Status:** Accepted

**Context:**
Need an HTTP server framework for agents.

**Decision:**
Use FastAPI with Uvicorn.

**Rationale:**
- Modern async Python framework
- Automatic OpenAPI documentation
- Excellent type hint support
- High performance

**Consequences:**
- (+) Clean API definitions
- (+) Auto-generated docs
- (+) Async support
- (-) Additional dependency

---

### ADR-004: Strategy Pattern for Players

**Status:** Accepted

**Context:**
Players need different decision-making strategies.

**Decision:**
Implement Strategy pattern with pluggable strategies.

**Rationale:**
- Easy to add new strategies
- Strategies are independently testable
- Clear interface contract

**Consequences:**
- (+) Extensible
- (+) Testable
- (+) Follows Open/Closed principle

---

### ADR-005: Circuit Breaker for Resilience

**Status:** Accepted

**Context:**
Need to handle agent failures gracefully.

**Decision:**
Implement Circuit Breaker pattern with RetryClient.

**Rationale:**
- Prevents cascade failures
- Allows system recovery
- Industry-standard pattern

**Consequences:**
- (+) Improved fault tolerance
- (+) Fast failure detection
- (-) Added complexity

---

## 7. Deployment Architecture

### 7.1 Single-Machine Deployment

```
┌────────────────────────────────────────────────────────────────────┐
│                        Host Machine                                 │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │
│  │ Python Process│  │ Python Process│  │ Python Process│          │
│  │ (League Mgr)  │  │  (Referee 1)  │  │  (Referee 2)  │          │
│  │   Port 8000   │  │   Port 8001   │  │   Port 8002   │          │
│  └───────────────┘  └───────────────┘  └───────────────┘          │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │
│  │ Python Process│  │ Python Process│  │ Python Process│  ···     │
│  │  (Player 1)   │  │  (Player 2)   │  │  (Player 3)   │          │
│  │   Port 8101   │  │   Port 8102   │  │   Port 8103   │          │
│  └───────────────┘  └───────────────┘  └───────────────┘          │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Shared File System                        │   │
│  │  SHARED/                                                     │   │
│  │  ├── config/    (Configuration files)                        │   │
│  │  ├── data/      (Runtime data - standings, matches)          │   │
│  │  └── logs/      (JSONL log files)                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### 7.2 Startup Sequence

```
1. League Manager (Port 8000)
   └── Wait for readiness (15s timeout)

2. Referees (Ports 8001-8002)
   ├── Start REF01
   │   └── Register with League Manager
   └── Start REF02
       └── Register with League Manager

3. Players (Ports 8101-8104)
   ├── Start P01 (random strategy)
   ├── Start P02 (history strategy)
   ├── Start P03 (adaptive strategy)
   └── Start P04 (random strategy)
   └── All register with League Manager
```

---

## 8. Security Architecture

### 8.1 Authentication Flow

```
┌────────────┐                    ┌────────────────┐
│   Agent    │  1. Register       │ League Manager │
│            │ ──────────────────▶│                │
│            │                    │                │
│            │  2. Generate Token │                │
│            │                    │  [32-byte      │
│            │                    │   random]      │
│            │                    │                │
│            │  3. Return Token   │                │
│            │ ◀────────────────── │                │
│            │                    │                │
│            │  4. Include Token  │                │
│            │     in Requests    │                │
│            │ ──────────────────▶│                │
│            │                    │  [Validate     │
│            │                    │   Token]       │
└────────────┘                    └────────────────┘
```

### 8.2 Security Controls

| Control | Implementation |
|---------|----------------|
| Authentication | Token-based after registration |
| Token Security | 32-byte random tokens |
| No Secrets in Code | All secrets via config/env |
| Input Validation | Validate all API inputs |
| Error Handling | No sensitive data in errors |

---

## Appendix A: Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| HTTP Client | httpx |
| Testing | pytest |
| Logging | Custom JsonLogger |
| Configuration | JSON files |
| Persistence | JSON files |

---

## Appendix B: Port Allocations

| Component | Port(s) |
|-----------|---------|
| League Manager | 8000 |
| Referees | 8001-8010 |
| Players | 8101-8200 |

---

*This Architecture Document follows the guidelines from "Guidelines for Submitting Outstanding Software" Version 2.0 and uses the C4 Model for software architecture documentation.*
