"""
Unit tests for Referee Handlers (game_logic module).

Tests the EvenOddGame class and related game logic functions
that are used by referee agents.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import pytest

# Add paths
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "SHARED"))
sys.path.insert(0, str(ROOT_DIR / "agents" / "referee_REF01"))

from game_logic import EvenOddGame, GameResult, GameState, MatchResult


class TestGameLogicConstants:
    """Tests for game logic constants."""

    def test_valid_choices(self):
        """Test valid parity choices."""
        game = EvenOddGame()
        assert "even" in game.VALID_CHOICES
        assert "odd" in game.VALID_CHOICES
        assert len(game.VALID_CHOICES) == 2

    def test_number_range(self):
        """Test number range constants."""
        game = EvenOddGame()
        assert game.MIN_NUMBER == 1
        assert game.MAX_NUMBER == 10

    def test_scoring_values(self):
        """Test scoring constants."""
        game = EvenOddGame()
        assert game.WIN_POINTS == 3
        assert game.DRAW_POINTS == 1
        assert game.LOSS_POINTS == 0


class TestGameState:
    """Tests for GameState enum."""

    def test_game_states_exist(self):
        """Test that all game states exist."""
        assert GameState.WAITING_FOR_PLAYERS is not None
        assert GameState.COLLECTING_CHOICES is not None
        assert GameState.DRAWING_NUMBER is not None
        assert GameState.FINISHED is not None

    def test_game_state_values(self):
        """Test GameState enum values."""
        assert GameState.WAITING_FOR_PLAYERS.value == "WAITING_FOR_PLAYERS"
        assert GameState.COLLECTING_CHOICES.value == "COLLECTING_CHOICES"
        assert GameState.FINISHED.value == "FINISHED"


class TestMatchResult:
    """Tests for MatchResult enum."""

    def test_match_results_exist(self):
        """Test that all match results exist."""
        assert MatchResult.WIN is not None
        assert MatchResult.DRAW is not None
        assert MatchResult.TECHNICAL_LOSS is not None

    def test_match_result_values(self):
        """Test MatchResult enum values."""
        assert MatchResult.WIN.value == "WIN"
        assert MatchResult.DRAW.value == "DRAW"
        assert MatchResult.TECHNICAL_LOSS.value == "TECHNICAL_LOSS"


class TestEvenOddGameInit:
    """Tests for EvenOddGame initialization."""

    def test_init_without_seed(self):
        """Test initialization without seed."""
        game = EvenOddGame()
        assert game is not None

    def test_init_with_seed(self):
        """Test initialization with seed."""
        game = EvenOddGame(seed=42)
        assert game is not None

    def test_init_game_state(self):
        """Test init_game_state method."""
        game = EvenOddGame()
        state = game.init_game_state("R1M1", "P01", "P02")

        assert state["match_id"] == "R1M1"
        assert state["state"] == "WAITING_FOR_PLAYERS"
        assert "P01" in state["players"]
        assert "P02" in state["players"]
        assert state["drawn_number"] is None
        assert state["result"] is None


class TestEvenOddGameValidation:
    """Tests for choice validation."""

    def test_validate_choice_even(self):
        """Test validation of 'even' choice."""
        game = EvenOddGame()
        assert game.validate_choice("even") == True

    def test_validate_choice_odd(self):
        """Test validation of 'odd' choice."""
        game = EvenOddGame()
        assert game.validate_choice("odd") == True

    def test_validate_choice_uppercase(self):
        """Test validation ignores case."""
        game = EvenOddGame()
        assert game.validate_choice("EVEN") == True
        assert game.validate_choice("ODD") == True
        assert game.validate_choice("Even") == True

    def test_validate_choice_invalid(self):
        """Test validation rejects invalid choices."""
        game = EvenOddGame()
        assert game.validate_choice("invalid") == False
        assert game.validate_choice("evn") == False

    def test_normalize_choice(self):
        """Test choice normalization."""
        game = EvenOddGame()
        assert game.normalize_choice("EVEN") == "even"
        assert game.normalize_choice("ODD") == "odd"
        assert game.normalize_choice("Even") == "even"

    def test_normalize_choice_invalid_raises(self):
        """Test normalization raises for invalid choice."""
        game = EvenOddGame()
        with pytest.raises(ValueError):
            game.normalize_choice("invalid")


class TestEvenOddGameNumberDraw:
    """Tests for random number drawing."""

    def test_draw_number_in_range(self):
        """Test drawn number is within range."""
        game = EvenOddGame()
        for _ in range(100):
            num = game.draw_number()
            assert 1 <= num <= 10

    def test_get_parity_even(self):
        """Test parity detection for even numbers."""
        game = EvenOddGame()
        assert game.get_parity(2) == "even"
        assert game.get_parity(4) == "even"
        assert game.get_parity(6) == "even"
        assert game.get_parity(8) == "even"
        assert game.get_parity(10) == "even"

    def test_get_parity_odd(self):
        """Test parity detection for odd numbers."""
        game = EvenOddGame()
        assert game.get_parity(1) == "odd"
        assert game.get_parity(3) == "odd"
        assert game.get_parity(5) == "odd"
        assert game.get_parity(7) == "odd"
        assert game.get_parity(9) == "odd"


class TestEvenOddGameDetermineWinner:
    """Tests for winner determination."""

    def test_determine_winner_player_a_wins(self):
        """Test when player A wins (correct, B wrong)."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=4  # even
        )

        assert result.winner_player_id == "P01"
        assert result.status == MatchResult.WIN

    def test_determine_winner_player_b_wins(self):
        """Test when player B wins (correct, A wrong)."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=3  # odd
        )

        assert result.winner_player_id == "P02"
        assert result.status == MatchResult.WIN

    def test_determine_winner_draw_both_correct(self):
        """Test draw when both players correct."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="even",
            drawn_number=4  # even
        )

        assert result.status == MatchResult.DRAW
        assert result.winner_player_id is None

    def test_determine_winner_draw_both_wrong(self):
        """Test draw when both players wrong."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="odd",
            choice_b="odd",
            drawn_number=4  # even
        )

        assert result.status == MatchResult.DRAW
        assert result.winner_player_id is None

    def test_determine_winner_with_random_draw(self):
        """Test winner determination with random number."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd"
        )

        assert result.status in [MatchResult.WIN, MatchResult.DRAW]
        assert result.drawn_number is not None
        assert 1 <= result.drawn_number <= 10

    def test_determine_winner_scores_correct(self):
        """Test that scores are correctly assigned."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=4  # P01 wins
        )

        assert result.scores["P01"] == 3  # WIN_POINTS
        assert result.scores["P02"] == 0  # LOSS_POINTS


class TestEvenOddGameTechnicalLoss:
    """Tests for technical loss scenarios."""

    def test_create_technical_loss_player_a_loses(self):
        """Test technical loss for player A."""
        game = EvenOddGame()

        result = game.create_technical_loss(
            player_a="P01",
            player_b="P02",
            losing_player="P01",
            reason="TIMEOUT"
        )

        assert result.winner_player_id == "P02"
        assert result.status == MatchResult.TECHNICAL_LOSS
        assert "TIMEOUT" in result.reason

    def test_create_technical_loss_player_b_loses(self):
        """Test technical loss for player B."""
        game = EvenOddGame()

        result = game.create_technical_loss(
            player_a="P01",
            player_b="P02",
            losing_player="P02",
            reason="CONNECTION_ERROR"
        )

        assert result.winner_player_id == "P01"
        assert result.status == MatchResult.TECHNICAL_LOSS

    def test_create_technical_loss_scores(self):
        """Test scores in technical loss."""
        game = EvenOddGame()

        result = game.create_technical_loss(
            player_a="P01",
            player_b="P02",
            losing_player="P02",
            reason="TIMEOUT"
        )

        assert result.scores["P01"] == 3  # Winner gets WIN_POINTS
        assert result.scores["P02"] == 0  # Loser gets LOSS_POINTS


class TestGameResult:
    """Tests for GameResult dataclass."""

    def test_game_result_creation(self):
        """Test GameResult creation."""
        result = GameResult(
            status=MatchResult.WIN,
            winner_player_id="P01",
            drawn_number=4,
            number_parity="even",
            choices={"P01": "even", "P02": "odd"},
            reason="correct_guess",
            scores={"P01": 3, "P02": 0}
        )

        assert result.winner_player_id == "P01"
        assert result.status == MatchResult.WIN
        assert result.scores["P01"] == 3

    def test_result_to_dict(self):
        """Test result_to_dict conversion."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=4
        )

        result_dict = game.result_to_dict(result)

        assert isinstance(result_dict, dict)
        assert "status" in result_dict
        assert "winner_player_id" in result_dict
        assert "drawn_number" in result_dict
        assert "scores" in result_dict


class TestEvenOddGameEdgeCases:
    """Tests for edge cases."""

    def test_same_choices_even_number(self):
        """Test both players choose even, number is even."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="even",
            drawn_number=2
        )

        assert result.status == MatchResult.DRAW

    def test_same_choices_odd_number(self):
        """Test both players choose odd, number is odd."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="odd",
            choice_b="odd",
            drawn_number=7
        )

        assert result.status == MatchResult.DRAW

    def test_boundary_numbers(self):
        """Test boundary numbers (1 and 10)."""
        game = EvenOddGame()

        # Test with 1 (odd, minimum)
        result1 = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="odd",
            choice_b="even",
            drawn_number=1
        )
        assert result1.winner_player_id == "P01"

        # Test with 10 (even, maximum)
        result10 = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=10
        )
        assert result10.winner_player_id == "P01"

    def test_case_insensitive_choices(self):
        """Test choices are normalized before comparison."""
        game = EvenOddGame()

        # Normalize before calling determine_winner
        choice_a = game.normalize_choice("EVEN")
        choice_b = game.normalize_choice("ODD")

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a=choice_a,
            choice_b=choice_b,
            drawn_number=4
        )

        assert result.winner_player_id == "P01"

    def test_choices_stored_in_result(self):
        """Test that choices are stored in result."""
        game = EvenOddGame()

        result = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=4
        )

        assert result.choices["P01"] == "even"
        assert result.choices["P02"] == "odd"

    def test_number_parity_stored_in_result(self):
        """Test that number parity is stored in result."""
        game = EvenOddGame()

        result_even = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=4
        )
        assert result_even.number_parity == "even"

        result_odd = game.determine_winner(
            player_a="P01",
            player_b="P02",
            choice_a="even",
            choice_b="odd",
            drawn_number=5
        )
        assert result_odd.number_parity == "odd"
