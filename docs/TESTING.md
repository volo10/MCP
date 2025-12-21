# Testing Documentation

This document describes the testing strategy and test suites for the MCP League System.

---

## Overview

The project includes comprehensive unit tests covering:

- **SDK Components**: Config models, config loader, repositories, logger
- **Game Logic**: Even/Odd game rules, scoring, result determination
- **Strategies**: Random, history-based, and adaptive strategies
- **Scheduler**: Round-Robin scheduling algorithm
- **Resilience**: Retry logic, circuit breaker
- **Protocol**: Message envelope format, JSON-RPC format

---

## Running Tests

### Prerequisites

```bash
pip install pytest
```

### Run All Tests

```bash
# From project root (L07/)
pytest

# With verbose output
pytest -v

# With coverage (requires pytest-cov)
pip install pytest-cov
pytest --cov=SHARED/league_sdk --cov=agents
```

### Run Specific Test Files

```bash
# Test config models
pytest tests/test_config_models.py

# Test game logic
pytest tests/test_game_logic.py

# Test strategies
pytest tests/test_strategy.py
```

### Run Specific Test Classes

```bash
# Test only EvenOddGame
pytest tests/test_game_logic.py::TestEvenOddGame

# Test only RandomStrategy
pytest tests/test_strategy.py::TestRandomStrategy
```

### Run Specific Tests

```bash
# Test player win scenario
pytest tests/test_game_logic.py::TestEvenOddGame::test_determine_winner_player_a_wins
```

---

## Test Suites

### 1. Config Models (`test_config_models.py`)

Tests for dataclass definitions:

| Test Class | Description |
|------------|-------------|
| `TestNetworkConfig` | Network configuration |
| `TestSecurityConfig` | Security settings |
| `TestTimeoutsConfig` | Timeout values |
| `TestRetryPolicyConfig` | Retry policy |
| `TestRefereeConfig` | Referee configuration |
| `TestPlayerConfig` | Player configuration |
| `TestScoringConfig` | Scoring rules |
| `TestLeagueConfig` | League configuration |

### 2. Config Loader (`test_config_loader.py`)

Tests for configuration loading:

| Test | Description |
|------|-------------|
| `test_load_system_config` | Load system.json |
| `test_load_system_config_cached` | Verify caching |
| `test_load_agents_config` | Load agents config |
| `test_load_league_config` | Load league config |
| `test_get_referee_by_id` | Get referee by ID |
| `test_get_player_by_id` | Get player by ID |
| `test_clear_cache` | Cache clearing |

### 3. Repositories (`test_repositories.py`)

Tests for data persistence:

| Test Class | Description |
|------------|-------------|
| `TestStandingsRepository` | Standings CRUD |
| `TestMatchRepository` | Match transcript |
| `TestPlayerHistoryRepository` | Player history |

Key tests:
- `test_save_and_load` - Persistence
- `test_update_player_win` - Score updates
- `test_ranking_order` - Ranking calculation
- `test_create_match` - Match creation
- `test_add_transcript_entry` - Logging moves

### 4. Logger (`test_logger.py`)

Tests for JSONL logging:

| Test | Description |
|------|-------------|
| `test_log_basic` | Basic logging |
| `test_log_timestamp_format` | ISO 8601 format |
| `test_log_info` | INFO level |
| `test_log_error` | ERROR level |
| `test_log_message_sent` | Message tracking |

### 5. Game Logic (`test_game_logic.py`)

Tests for Even/Odd game:

| Test Class | Description |
|------------|-------------|
| `TestEvenOddGame` | Game rules |
| `TestGameResult` | Result dataclass |
| `TestGameState` | State enum |
| `TestMatchResult` | Result enum |

Key tests:
- `test_validate_choice_even` - Choice validation
- `test_determine_winner_player_a_wins` - Win scenario
- `test_determine_winner_draw_both_correct` - Draw scenario
- `test_create_technical_loss` - Timeout handling

### 6. Strategy (`test_strategy.py`)

Tests for player strategies:

| Test Class | Description |
|------------|-------------|
| `TestRandomStrategy` | Random choice |
| `TestHistoryBasedStrategy` | History analysis |
| `TestAdaptiveStrategy` | Opponent tracking |
| `TestStrategyManager` | Strategy factory |

Key tests:
- `test_choose_valid_output` - Valid choices
- `test_choose_distribution` - 50/50 distribution
- `test_update_win` - Learning from wins
- `test_switch_strategy` - Strategy switching

### 7. Scheduler (`test_scheduler.py`)

Tests for Round-Robin scheduling:

| Test | Description |
|------|-------------|
| `test_create_schedule_4_players` | 4 player schedule |
| `test_each_player_plays_all_others` | Complete pairing |
| `test_no_duplicate_matches` | No duplicates |
| `test_no_self_play` | No self-matches |
| `test_get_total_matches` | Match count (n(n-1)/2) |

### 8. Resilience (`test_resilience.py`)

Tests for fault tolerance:

| Test Class | Description |
|------------|-------------|
| `TestErrorCode` | Error codes |
| `TestRetryableError` | Error exception |
| `TestRetryClient` | Retry logic |
| `TestCircuitBreaker` | Circuit breaker |

Key tests:
- `test_calculate_delay_exponential` - Backoff calculation
- `test_opens_after_threshold` - Circuit opens
- `test_half_open_success_closes` - Recovery

### 9. Envelope (`test_envelope.py`)

Tests for message format:

| Test Class | Description |
|------------|-------------|
| `TestEnvelopeFormat` | Envelope structure |
| `TestJsonRpcFormat` | JSON-RPC 2.0 |
| `TestMessageTypes` | Message type constants |

---

## Fixtures (conftest.py)

Available pytest fixtures:

| Fixture | Description |
|---------|-------------|
| `config_loader` | ConfigLoader instance |
| `temp_data_dir` | Temporary data directory |
| `temp_logs_dir` | Temporary logs directory |
| `sample_players` | ["P01", "P02", "P03", "P04"] |
| `sample_match` | Match data dict |
| `sample_envelope` | Message envelope dict |
| `standings_repository` | StandingsRepository |
| `match_repository` | MatchRepository |
| `json_logger` | JsonLogger |
| `even_odd_game` | EvenOddGame (seed=42) |
| `random_strategy` | RandomStrategy (seed=42) |
| `scheduler` | RoundRobinScheduler |

---

## Test Coverage Goals

| Component | Target Coverage |
|-----------|-----------------|
| Config Models | 100% |
| Config Loader | 95% |
| Repositories | 95% |
| Logger | 90% |
| Game Logic | 100% |
| Strategy | 95% |
| Scheduler | 100% |
| Resilience | 90% |

---

## Writing New Tests

### Test File Template

```python
"""
Unit tests for new_module.py
"""

import sys
from pathlib import Path

# Add paths as needed
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

import unittest


class TestNewFeature(unittest.TestCase):
    """Tests for NewFeature class."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
    
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
```

### Best Practices

1. **One assertion per test** when possible
2. **Descriptive test names**: `test_<method>_<scenario>_<expected>`
3. **Use fixtures** for common setup
4. **Test edge cases**: empty, null, boundary values
5. **Test error conditions**: exceptions, invalid input
6. **Keep tests fast**: mock external dependencies

---

## Integration Tests

For full system integration tests, use `test_system.py`:

```bash
python test_system.py
```

This runs:
- SDK import verification
- Config loading tests
- Envelope format tests
- JSON-RPC format tests
- Game logic tests
- Strategy tests
- Resilience tests

---

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install pytest pytest-cov
      - run: pytest --cov=SHARED/league_sdk --cov-report=xml
```

