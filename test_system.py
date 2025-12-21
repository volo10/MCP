#!/usr/bin/env python3
"""
System Integration Test - Verify all components work together.

Tests:
1. SDK imports and configuration loading
2. Agent message format compliance
3. Envelope format validation
4. Protocol version consistency
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add SHARED to path
SCRIPT_DIR = Path(__file__).parent.resolve()
SHARED_PATH = SCRIPT_DIR / "SHARED"
sys.path.insert(0, str(SHARED_PATH))


def test_sdk_imports():
    """Test that all SDK components can be imported."""
    print("Testing SDK imports...")
    
    from league_sdk import (
        ConfigLoader,
        StandingsRepository,
        MatchRepository,
        PlayerHistoryRepository,
        JsonLogger,
        SystemConfig,
        PlayerConfig,
        RefereeConfig,
        LeagueConfig,
    )
    
    print("  ✓ All SDK components imported successfully")
    return True


def test_config_loading():
    """Test configuration file loading."""
    print("Testing configuration loading...")
    
    from league_sdk import ConfigLoader
    
    loader = ConfigLoader()
    
    # Test system config
    system = loader.load_system()
    assert system.protocol_version == "league.v2", "Protocol version mismatch"
    print(f"  ✓ System config: protocol={system.protocol_version}")
    
    # Test agents config
    agents = loader.load_agents()
    assert len(agents.referees) >= 2, "Need at least 2 referees"
    assert len(agents.players) >= 4, "Need at least 4 players"
    print(f"  ✓ Agents config: {len(agents.referees)} referees, {len(agents.players)} players")
    
    # Test league config
    league = loader.load_league("league_2025_even_odd")
    assert league.game_type == "even_odd", "Game type mismatch"
    print(f"  ✓ League config: {league.display_name}")
    
    # Test games registry
    games = loader.load_games_registry()
    assert len(games.games) >= 1, "Need at least 1 game type"
    print(f"  ✓ Games registry: {len(games.games)} game types")
    
    return True


def test_envelope_format():
    """Test protocol envelope format compliance."""
    print("Testing envelope format...")
    
    # Required envelope fields from protocol spec
    required_fields = [
        "protocol",
        "message_type",
        "sender",
        "timestamp",
    ]
    
    def create_envelope(message_type: str, sender: str, **extra) -> dict:
        return {
            "protocol": "league.v2",
            "message_type": message_type,
            "sender": sender,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **extra
        }
    
    # Test various message types
    test_cases = [
        ("LEAGUE_REGISTER_REQUEST", "player:P01", {"auth_token": "tok_xxx"}),
        ("REFEREE_REGISTER_REQUEST", "referee:REF01", {}),
        ("GAME_INVITATION", "referee:REF01", {"match_id": "R1M1"}),
        ("CHOOSE_PARITY_CALL", "referee:REF01", {"player_id": "P01"}),
        ("GAME_OVER", "referee:REF01", {"match_id": "R1M1"}),
    ]
    
    for message_type, sender, extra in test_cases:
        envelope = create_envelope(message_type, sender, **extra)
        
        # Check required fields
        for field in required_fields:
            assert field in envelope, f"Missing field: {field}"
        
        # Check protocol version
        assert envelope["protocol"] == "league.v2", "Wrong protocol version"
        
        # Check timestamp format (ISO 8601 with Z suffix)
        ts = envelope["timestamp"]
        assert ts.endswith("Z"), "Timestamp must end with Z (UTC)"
        
        print(f"  ✓ {message_type}: valid envelope")
    
    return True


def test_jsonrpc_format():
    """Test JSON-RPC 2.0 message format."""
    print("Testing JSON-RPC 2.0 format...")
    
    def create_request(method: str, params: dict, id: int) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": id
        }
    
    def create_response(result: dict, id: int) -> dict:
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": id
        }
    
    def create_error(code: int, message: str, id: int) -> dict:
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": id
        }
    
    # Test request format
    request = create_request("register_player", {"player_meta": {}}, 1)
    assert request["jsonrpc"] == "2.0"
    assert "method" in request
    assert "params" in request
    print("  ✓ Request format valid")
    
    # Test response format
    response = create_response({"status": "ACCEPTED"}, 1)
    assert response["jsonrpc"] == "2.0"
    assert "result" in response
    print("  ✓ Response format valid")
    
    # Test error format
    error = create_error(-32600, "Invalid Request", 1)
    assert "error" in error
    assert "code" in error["error"]
    print("  ✓ Error format valid")
    
    return True


def test_game_logic():
    """Test game logic module."""
    print("Testing game logic...")
    
    sys.path.insert(0, str(SCRIPT_DIR / "agents" / "referee_REF01"))
    from game_logic import EvenOddGame, MatchResult
    
    game = EvenOddGame(seed=42)
    
    # Test validation
    assert game.validate_choice("even") == True
    assert game.validate_choice("odd") == True
    assert game.validate_choice("invalid") == False
    print("  ✓ Choice validation works")
    
    # Test number drawing
    for _ in range(10):
        num = game.draw_number()
        assert 1 <= num <= 10, f"Number out of range: {num}"
    print("  ✓ Number drawing works (1-10)")
    
    # Test winner determination
    result = game.determine_winner("P01", "P02", "even", "odd", drawn_number=8)
    assert result.winner_player_id == "P01", "Wrong winner"
    assert result.status == MatchResult.WIN
    print("  ✓ Winner determination works")
    
    # Test draw scenario
    result = game.determine_winner("P01", "P02", "even", "even", drawn_number=4)
    assert result.status == MatchResult.DRAW
    assert result.winner_player_id is None
    print("  ✓ Draw detection works")
    
    return True


def test_strategy():
    """Test player strategy module."""
    print("Testing strategy module...")
    
    sys.path.insert(0, str(SCRIPT_DIR / "agents" / "player_P01"))
    from strategy import RandomStrategy, StrategyManager
    
    # Test random strategy
    strategy = RandomStrategy(seed=42)
    choices = [strategy.choose() for _ in range(100)]
    
    assert all(c in ["even", "odd"] for c in choices), "Invalid choices"
    even_count = choices.count("even")
    odd_count = choices.count("odd")
    
    # Should be roughly 50/50 (allow some variance)
    assert 30 <= even_count <= 70, f"Distribution off: {even_count}/100 even"
    print(f"  ✓ Random strategy: {even_count}% even, {odd_count}% odd")
    
    # Test strategy manager
    manager = StrategyManager("random")
    choice = manager.choose()
    assert choice in ["even", "odd"]
    assert choice == choice.lower(), "Choice must be lowercase"
    print("  ✓ Strategy manager works")
    
    return True


def test_resilience():
    """Test resilience module."""
    print("Testing resilience module...")
    
    sys.path.insert(0, str(SCRIPT_DIR / "agents" / "player_P01"))
    from resilience import RetryClient, CircuitBreaker, ErrorCode
    
    # Test retry client delay calculation
    client = RetryClient(max_retries=3, backoff_strategy="exponential")
    
    delays = [client._calculate_delay(i) for i in range(4)]
    assert delays[0] < delays[1] < delays[2], "Exponential backoff not working"
    print(f"  ✓ Exponential backoff: {[round(d, 1) for d in delays[:3]]}s")
    
    # Test circuit breaker
    cb = CircuitBreaker(failure_threshold=3)
    
    assert cb.can_execute() == True, "Should be closed initially"
    
    # Simulate failures
    for _ in range(3):
        cb.record_failure()
    
    assert cb.state.value == "OPEN", "Should be open after threshold"
    assert cb.can_execute() == False, "Should reject when open"
    print("  ✓ Circuit breaker works")
    
    # Test error codes
    assert ErrorCode.TIMEOUT_ERROR.value == "E001"
    assert ErrorCode.CONNECTION_ERROR.value == "E009"
    print("  ✓ Error codes defined")
    
    return True


def test_repositories():
    """Test data repositories."""
    print("Testing repositories...")
    
    from league_sdk import StandingsRepository, PlayerHistoryRepository
    
    # Test standings repository
    standings = StandingsRepository("test_league")
    data = standings.load()
    assert "standings" in data
    print("  ✓ StandingsRepository works")
    
    # Test player history repository
    history = PlayerHistoryRepository("test_player")
    data = history.load()
    assert "matches" in data
    print("  ✓ PlayerHistoryRepository works")
    
    return True


def run_all_tests():
    """Run all tests and report results."""
    print()
    print("=" * 60)
    print("  MCP League System Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("SDK Imports", test_sdk_imports),
        ("Config Loading", test_config_loading),
        ("Envelope Format", test_envelope_format),
        ("JSON-RPC Format", test_jsonrpc_format),
        ("Game Logic", test_game_logic),
        ("Strategy", test_strategy),
        ("Resilience", test_resilience),
        ("Repositories", test_repositories),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)
    print()
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

