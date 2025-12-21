"""
Pytest configuration and fixtures for MCP League System tests.
"""

import sys
from pathlib import Path
import pytest

# Add paths
ROOT_DIR = Path(__file__).parent.parent
SHARED_DIR = ROOT_DIR / "SHARED"
AGENTS_DIR = ROOT_DIR / "agents"

# Add to Python path
sys.path.insert(0, str(SHARED_DIR))
sys.path.insert(0, str(AGENTS_DIR / "league_manager"))
sys.path.insert(0, str(AGENTS_DIR / "referee_REF01"))
sys.path.insert(0, str(AGENTS_DIR / "player_P01"))


@pytest.fixture
def config_loader():
    """Fixture for ConfigLoader."""
    from league_sdk.config_loader import ConfigLoader
    return ConfigLoader()


@pytest.fixture
def temp_data_dir(tmp_path):
    """Fixture for temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_logs_dir(tmp_path):
    """Fixture for temporary logs directory."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    return logs_dir


@pytest.fixture
def sample_players():
    """Fixture for sample player list."""
    return ["P01", "P02", "P03", "P04"]


@pytest.fixture
def sample_match():
    """Fixture for sample match data."""
    return {
        "match_id": "R1M1",
        "round_id": 1,
        "game_type": "even_odd",
        "player_a": "P01",
        "player_b": "P02",
        "referee_id": "REF01"
    }


@pytest.fixture
def sample_envelope():
    """Fixture for sample message envelope."""
    from datetime import datetime, timezone
    
    return {
        "protocol": "league.v2",
        "message_type": "GAME_INVITATION",
        "sender": "referee:REF01",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "auth_token": "tok_test_abc123",
        "conversation_id": "conv-r1m1-001",
        "league_id": "league_2025_even_odd",
        "round_id": 1,
        "match_id": "R1M1"
    }


@pytest.fixture
def standings_repository(temp_data_dir):
    """Fixture for StandingsRepository."""
    from league_sdk.repositories import StandingsRepository
    return StandingsRepository("test_league", data_root=temp_data_dir)


@pytest.fixture
def match_repository(temp_data_dir):
    """Fixture for MatchRepository."""
    from league_sdk.repositories import MatchRepository
    return MatchRepository("test_league", data_root=temp_data_dir)


@pytest.fixture
def player_history_repository(temp_data_dir):
    """Fixture for PlayerHistoryRepository."""
    from league_sdk.repositories import PlayerHistoryRepository
    return PlayerHistoryRepository("P01", data_root=temp_data_dir)


@pytest.fixture
def json_logger(temp_logs_dir):
    """Fixture for JsonLogger."""
    from league_sdk.logger import JsonLogger
    return JsonLogger("test_component", logs_root=temp_logs_dir)


@pytest.fixture
def even_odd_game():
    """Fixture for EvenOddGame with fixed seed."""
    from game_logic import EvenOddGame
    return EvenOddGame(seed=42)


@pytest.fixture
def random_strategy():
    """Fixture for RandomStrategy with fixed seed."""
    from strategy import RandomStrategy
    return RandomStrategy(seed=42)


@pytest.fixture
def scheduler():
    """Fixture for RoundRobinScheduler."""
    from scheduler import RoundRobinScheduler
    return RoundRobinScheduler()

