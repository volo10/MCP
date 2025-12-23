"""
Unit tests for Player Handlers.

Tests the PlayerHandlers class which handles:
- GAME_INVITATION
- CHOOSE_PARITY_CALL
- GAME_OVER
- Notifications (ROUND_ANNOUNCEMENT, STANDINGS_UPDATE, etc.)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock
import pytest

# Add paths
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "SHARED"))
sys.path.insert(0, str(ROOT_DIR / "agents" / "player_P01"))

from handlers import PlayerHandlers


class MockPlayerState:
    """Mock PlayerState for testing handlers."""

    def __init__(self):
        self.player_id = "P01"
        self.auth_token = "tok_test_123"
        self.league_id = "test_league"
        self.current_match = None
        self.strategy_manager = None
        self.history_repo = None
        self.strategy_type = "random"
        self.logger = Mock()
        self.logger.info = Mock()
        self.logger.debug = Mock()
        self.logger.error = Mock()


@pytest.fixture
def mock_state():
    """Fixture for mock player state."""
    return MockPlayerState()


@pytest.fixture
def player_handlers(mock_state):
    """Fixture for PlayerHandlers."""
    return PlayerHandlers(mock_state)


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestPlayerHandlersInit:
    """Tests for PlayerHandlers initialization."""

    def test_init_with_state(self, mock_state):
        """Test handler initializes with state."""
        handlers = PlayerHandlers(mock_state)
        assert handlers.state == mock_state

    def test_create_envelope_basic(self, player_handlers):
        """Test envelope creation with basic fields."""
        envelope = player_handlers._create_envelope("TEST_MESSAGE")

        assert envelope["protocol"] == "league.v2"
        assert envelope["message_type"] == "TEST_MESSAGE"
        assert envelope["sender"] == "player:P01"
        assert "timestamp" in envelope
        assert envelope["auth_token"] == "tok_test_123"

    def test_create_envelope_with_extra_fields(self, player_handlers):
        """Test envelope creation with extra fields."""
        envelope = player_handlers._create_envelope(
            "TEST_MESSAGE",
            match_id="R1M1",
            custom_field="value"
        )

        assert envelope["match_id"] == "R1M1"
        assert envelope["custom_field"] == "value"

    def test_create_envelope_unregistered(self, mock_state):
        """Test envelope for unregistered player."""
        mock_state.player_id = None
        handlers = PlayerHandlers(mock_state)
        envelope = handlers._create_envelope("TEST")

        assert envelope["sender"] == "player:UNREGISTERED"

    def test_create_envelope_no_auth_token(self, mock_state):
        """Test envelope without auth token."""
        mock_state.auth_token = None
        handlers = PlayerHandlers(mock_state)
        envelope = handlers._create_envelope("TEST")

        assert "auth_token" not in envelope


class TestHandleGameInvitation:
    """Tests for handle_game_invitation method."""

    def test_handle_game_invitation_success(self, player_handlers, mock_state):
        """Test successful game invitation handling."""
        params = {
            "match_id": "R1M1",
            "round_id": 1,
            "game_type": "even_odd",
            "opponent_id": "P02",
            "role_in_match": "player_A",
            "conversation_id": "conv-001"
        }

        response = run_async(player_handlers.handle_game_invitation(params))

        assert response["message_type"] == "GAME_JOIN_ACK"
        assert response["match_id"] == "R1M1"
        assert response["player_id"] == "P01"
        assert response["accept"] == True
        assert "arrival_timestamp" in response

    def test_handle_game_invitation_stores_match(self, player_handlers, mock_state):
        """Test that invitation stores match info."""
        params = {
            "match_id": "R1M1",
            "round_id": 1,
            "game_type": "even_odd",
            "opponent_id": "P02",
            "role_in_match": "player_A",
            "conversation_id": "conv-001"
        }

        run_async(player_handlers.handle_game_invitation(params))

        assert mock_state.current_match is not None
        assert mock_state.current_match["match_id"] == "R1M1"
        assert mock_state.current_match["opponent_id"] == "P02"
        assert mock_state.current_match["role"] == "player_A"

    def test_handle_game_invitation_logs(self, player_handlers, mock_state):
        """Test that invitation is logged."""
        params = {
            "match_id": "R1M1",
            "round_id": 1,
            "game_type": "even_odd",
            "opponent_id": "P02",
            "role_in_match": "player_B",
            "conversation_id": "conv-001"
        }

        run_async(player_handlers.handle_game_invitation(params))

        mock_state.logger.info.assert_called()


class TestHandleChooseParity:
    """Tests for handle_choose_parity method."""

    def test_handle_choose_parity_with_strategy(self, player_handlers, mock_state):
        """Test parity choice with strategy manager."""
        mock_strategy = Mock()
        mock_strategy.choose = Mock(return_value="even")
        mock_state.strategy_manager = mock_strategy

        params = {
            "match_id": "R1M1",
            "player_id": "P01",
            "game_type": "even_odd",
            "context": {"opponent_id": "P02"},
            "deadline": "2025-01-15T12:00:00Z",
            "conversation_id": "conv-001"
        }

        response = run_async(player_handlers.handle_choose_parity(params))

        assert response["message_type"] == "CHOOSE_PARITY_RESPONSE"
        assert response["parity_choice"] in ["even", "odd"]
        assert response["match_id"] == "R1M1"

    def test_handle_choose_parity_fallback_random(self, player_handlers, mock_state):
        """Test parity choice fallback to random."""
        mock_state.strategy_manager = None

        params = {
            "match_id": "R1M1",
            "player_id": "P01",
            "game_type": "even_odd",
            "context": {},
            "conversation_id": "conv-001"
        }

        response = run_async(player_handlers.handle_choose_parity(params))

        assert response["parity_choice"] in ["even", "odd"]

    def test_handle_choose_parity_stores_choice(self, player_handlers, mock_state):
        """Test that choice is stored in current match."""
        mock_state.current_match = {"match_id": "R1M1"}
        mock_state.strategy_manager = Mock()
        mock_state.strategy_manager.choose = Mock(return_value="ODD")  # uppercase

        params = {
            "match_id": "R1M1",
            "player_id": "P01",
            "game_type": "even_odd",
            "context": {},
            "conversation_id": "conv-001"
        }

        run_async(player_handlers.handle_choose_parity(params))

        assert mock_state.current_match["my_choice"] == "odd"  # lowercase

    def test_handle_choose_parity_normalizes_case(self, player_handlers, mock_state):
        """Test that choice is normalized to lowercase."""
        mock_state.strategy_manager = Mock()
        mock_state.strategy_manager.choose = Mock(return_value="EVEN")

        params = {
            "match_id": "R1M1",
            "player_id": "P01",
            "game_type": "even_odd",
            "context": {},
            "conversation_id": "conv-001"
        }

        response = run_async(player_handlers.handle_choose_parity(params))

        assert response["parity_choice"] == "even"


class TestHandleGameOver:
    """Tests for handle_game_over method."""

    def test_handle_game_over_win(self, player_handlers, mock_state):
        """Test game over with win."""
        params = {
            "match_id": "R1M1",
            "game_result": {
                "status": "COMPLETED",
                "winner_player_id": "P01",
                "drawn_number": 4,
                "number_parity": "even",
                "choices": {"P01": "even", "P02": "odd"},
                "reason": "correct_guess"
            }
        }

        response = run_async(player_handlers.handle_game_over(params))

        assert response["status"] == "received"
        assert response["result"] == "WIN"
        assert response["match_id"] == "R1M1"

    def test_handle_game_over_loss(self, player_handlers, mock_state):
        """Test game over with loss."""
        params = {
            "match_id": "R1M1",
            "game_result": {
                "status": "COMPLETED",
                "winner_player_id": "P02",
                "drawn_number": 3,
                "number_parity": "odd",
                "choices": {"P01": "even", "P02": "odd"},
                "reason": "correct_guess"
            }
        }

        response = run_async(player_handlers.handle_game_over(params))

        assert response["result"] == "LOSS"

    def test_handle_game_over_draw(self, player_handlers, mock_state):
        """Test game over with draw."""
        params = {
            "match_id": "R1M1",
            "game_result": {
                "status": "DRAW",
                "winner_player_id": None,
                "drawn_number": 4,
                "number_parity": "even",
                "choices": {"P01": "even", "P02": "even"},
                "reason": "both_correct"
            }
        }

        response = run_async(player_handlers.handle_game_over(params))

        assert response["result"] == "DRAW"

    def test_handle_game_over_updates_history(self, player_handlers, mock_state):
        """Test game over updates history repository."""
        mock_history = Mock()
        mock_history.add_match = Mock()
        mock_state.history_repo = mock_history

        params = {
            "match_id": "R1M1",
            "game_result": {
                "status": "COMPLETED",
                "winner_player_id": "P01",
                "drawn_number": 4,
                "number_parity": "even",
                "choices": {"P01": "even", "P02": "odd"},
                "reason": "correct_guess"
            }
        }

        run_async(player_handlers.handle_game_over(params))

        mock_history.add_match.assert_called_once()

    def test_handle_game_over_updates_strategy(self, player_handlers, mock_state):
        """Test game over updates strategy."""
        mock_strategy = Mock()
        mock_strategy.update = Mock()
        mock_state.strategy_manager = mock_strategy

        params = {
            "match_id": "R1M1",
            "game_result": {
                "status": "COMPLETED",
                "winner_player_id": "P01",
                "drawn_number": 4,
                "number_parity": "even",
                "choices": {"P01": "even", "P02": "odd"},
                "reason": "correct_guess"
            }
        }

        run_async(player_handlers.handle_game_over(params))

        mock_strategy.update.assert_called_once()

    def test_handle_game_over_clears_current_match(self, player_handlers, mock_state):
        """Test game over clears current match."""
        mock_state.current_match = {"match_id": "R1M1"}

        params = {
            "match_id": "R1M1",
            "game_result": {
                "status": "COMPLETED",
                "winner_player_id": "P01",
                "drawn_number": 4,
                "number_parity": "even",
                "choices": {"P01": "even", "P02": "odd"}
            }
        }

        run_async(player_handlers.handle_game_over(params))

        assert mock_state.current_match is None


class TestHandleNotification:
    """Tests for handle_notification method."""

    def test_handle_notification_round_announcement(self, player_handlers, mock_state):
        """Test handling ROUND_ANNOUNCEMENT notification."""
        params = {
            "message_type": "ROUND_ANNOUNCEMENT",
            "round_id": 1,
            "matches": [
                {"match_id": "R1M1", "player_A_id": "P01", "player_B_id": "P02"},
                {"match_id": "R1M2", "player_A_id": "P03", "player_B_id": "P04"}
            ]
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["status"] == "acknowledged"
        assert response["round_id"] == 1
        assert response["matches_count"] == 1  # Only P01's match

    def test_handle_notification_standings_update(self, player_handlers, mock_state):
        """Test handling LEAGUE_STANDINGS_UPDATE notification."""
        params = {
            "message_type": "LEAGUE_STANDINGS_UPDATE",
            "round_id": 1,
            "standings": [
                {"player_id": "P01", "rank": 1, "points": 3, "played": 1, "wins": 1, "draws": 0, "losses": 0},
                {"player_id": "P02", "rank": 2, "points": 0, "played": 1, "wins": 0, "draws": 0, "losses": 1}
            ]
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["status"] == "acknowledged"
        assert response["message_type"] == "LEAGUE_STANDINGS_UPDATE"
        assert response["my_rank"] == 1

    def test_handle_notification_round_completed(self, player_handlers, mock_state):
        """Test handling ROUND_COMPLETED notification."""
        params = {
            "message_type": "ROUND_COMPLETED",
            "round_id": 1,
            "matches_completed": 2,
            "next_round_id": 2
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["status"] == "acknowledged"
        assert response["message_type"] == "ROUND_COMPLETED"
        assert response["next_round_id"] == 2

    def test_handle_notification_round_completed_alt_field(self, player_handlers, mock_state):
        """Test handling ROUND_COMPLETED with matches_played field."""
        params = {
            "message_type": "ROUND_COMPLETED",
            "round_id": 1,
            "matches_played": 2,  # Alternative field name
            "next_round_id": 2
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["status"] == "acknowledged"

    def test_handle_notification_league_completed(self, player_handlers, mock_state):
        """Test handling LEAGUE_COMPLETED notification."""
        params = {
            "message_type": "LEAGUE_COMPLETED",
            "champion": {"player_id": "P01", "display_name": "Player 1", "points": 9},
            "total_rounds": 3,
            "total_matches": 6,
            "final_standings": [
                {"player_id": "P01", "rank": 1, "points": 9}
            ]
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["status"] == "acknowledged"
        assert response["message_type"] == "LEAGUE_COMPLETED"
        assert response["am_champion"] == True
        assert response["my_final_rank"] == 1

    def test_handle_notification_league_completed_not_champion(self, player_handlers, mock_state):
        """Test handling LEAGUE_COMPLETED when not champion."""
        params = {
            "message_type": "LEAGUE_COMPLETED",
            "champion": {"player_id": "P02", "display_name": "Player 2", "points": 9},
            "total_rounds": 3,
            "total_matches": 6,
            "final_standings": [
                {"player_id": "P02", "rank": 1, "points": 9},
                {"player_id": "P01", "rank": 2, "points": 6}
            ]
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["am_champion"] == False
        assert response["my_final_rank"] == 2

    def test_handle_notification_unknown_type(self, player_handlers, mock_state):
        """Test handling unknown notification type."""
        params = {
            "message_type": "UNKNOWN_TYPE"
        }

        response = run_async(player_handlers.handle_notification(params))

        assert response["status"] == "ignored"
        assert response["message_type"] == "UNKNOWN_TYPE"


class TestQueryHandlers:
    """Tests for query handler methods."""

    def test_get_stats_with_history(self, player_handlers, mock_state):
        """Test get_stats with history repository."""
        mock_history = Mock()
        mock_history.get_stats = Mock(return_value={"wins": 5, "losses": 3})
        mock_history.get_win_rate = Mock(return_value=0.625)
        mock_state.history_repo = mock_history
        mock_state.strategy_type = "random"

        response = run_async(player_handlers.get_stats())

        assert response["player_id"] == "P01"
        assert response["stats"] == {"wins": 5, "losses": 3}
        assert response["win_rate"] == 0.625
        assert response["strategy"] == "random"

    def test_get_stats_without_history(self, player_handlers, mock_state):
        """Test get_stats without history repository."""
        mock_state.history_repo = None
        mock_state.strategy_type = "adaptive"

        response = run_async(player_handlers.get_stats())

        assert response["player_id"] == "P01"
        assert response["stats"] == {}
        assert response["win_rate"] == 0

    def test_get_history_with_repo(self, player_handlers, mock_state):
        """Test get_history with history repository."""
        mock_history = Mock()
        mock_history.get_matches = Mock(return_value=[
            {"match_id": "R1M1", "result": "WIN"},
            {"match_id": "R2M1", "result": "LOSS"}
        ])
        mock_state.history_repo = mock_history

        response = run_async(player_handlers.get_history({"limit": 5}))

        assert response["player_id"] == "P01"
        assert len(response["matches"]) == 2
        mock_history.get_matches.assert_called_with(limit=5)

    def test_get_history_default_limit(self, player_handlers, mock_state):
        """Test get_history with default limit."""
        mock_history = Mock()
        mock_history.get_matches = Mock(return_value=[])
        mock_state.history_repo = mock_history

        run_async(player_handlers.get_history({}))

        mock_history.get_matches.assert_called_with(limit=10)

    def test_get_history_without_repo(self, player_handlers, mock_state):
        """Test get_history without history repository."""
        mock_state.history_repo = None

        response = run_async(player_handlers.get_history({"limit": 5}))

        assert response["player_id"] == "P01"
        assert response["matches"] == []
