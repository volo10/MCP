"""
Unit tests for game_logic.py (Even/Odd game)
"""

import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "referee_REF01"))

import unittest
from game_logic import EvenOddGame, GameState, MatchResult, GameResult


class TestEvenOddGame(unittest.TestCase):
    """Tests for EvenOddGame class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.game = EvenOddGame(seed=42)  # Fixed seed for reproducibility
    
    def test_validate_choice_even(self):
        """Test validating 'even' choice."""
        self.assertTrue(self.game.validate_choice("even"))
        self.assertTrue(self.game.validate_choice("EVEN"))
        self.assertTrue(self.game.validate_choice("Even"))
    
    def test_validate_choice_odd(self):
        """Test validating 'odd' choice."""
        self.assertTrue(self.game.validate_choice("odd"))
        self.assertTrue(self.game.validate_choice("ODD"))
        self.assertTrue(self.game.validate_choice("Odd"))
    
    def test_validate_choice_invalid(self):
        """Test validating invalid choices."""
        self.assertFalse(self.game.validate_choice(""))
        self.assertFalse(self.game.validate_choice("maybe"))
        self.assertFalse(self.game.validate_choice("1"))
        self.assertFalse(self.game.validate_choice("evn"))
    
    def test_normalize_choice(self):
        """Test normalizing choices to lowercase."""
        self.assertEqual(self.game.normalize_choice("EVEN"), "even")
        self.assertEqual(self.game.normalize_choice("ODD"), "odd")
        self.assertEqual(self.game.normalize_choice("Even"), "even")
    
    def test_normalize_choice_invalid(self):
        """Test normalizing invalid choice raises error."""
        with self.assertRaises(ValueError):
            self.game.normalize_choice("invalid")
    
    def test_draw_number_range(self):
        """Test that drawn numbers are in valid range."""
        game = EvenOddGame()  # No seed for random testing
        
        for _ in range(100):
            num = game.draw_number()
            self.assertGreaterEqual(num, 1)
            self.assertLessEqual(num, 10)
    
    def test_get_parity_even(self):
        """Test getting parity for even numbers."""
        self.assertEqual(self.game.get_parity(2), "even")
        self.assertEqual(self.game.get_parity(4), "even")
        self.assertEqual(self.game.get_parity(6), "even")
        self.assertEqual(self.game.get_parity(8), "even")
        self.assertEqual(self.game.get_parity(10), "even")
    
    def test_get_parity_odd(self):
        """Test getting parity for odd numbers."""
        self.assertEqual(self.game.get_parity(1), "odd")
        self.assertEqual(self.game.get_parity(3), "odd")
        self.assertEqual(self.game.get_parity(5), "odd")
        self.assertEqual(self.game.get_parity(7), "odd")
        self.assertEqual(self.game.get_parity(9), "odd")
    
    def test_determine_winner_player_a_wins(self):
        """Test when player A wins."""
        result = self.game.determine_winner(
            "P01", "P02", "even", "odd", drawn_number=8
        )
        
        self.assertEqual(result.status, MatchResult.WIN)
        self.assertEqual(result.winner_player_id, "P01")
        self.assertEqual(result.drawn_number, 8)
        self.assertEqual(result.number_parity, "even")
        self.assertEqual(result.scores["P01"], 3)
        self.assertEqual(result.scores["P02"], 0)
    
    def test_determine_winner_player_b_wins(self):
        """Test when player B wins."""
        result = self.game.determine_winner(
            "P01", "P02", "even", "odd", drawn_number=7
        )
        
        self.assertEqual(result.status, MatchResult.WIN)
        self.assertEqual(result.winner_player_id, "P02")
        self.assertEqual(result.scores["P01"], 0)
        self.assertEqual(result.scores["P02"], 3)
    
    def test_determine_winner_draw_both_correct(self):
        """Test draw when both players are correct."""
        result = self.game.determine_winner(
            "P01", "P02", "even", "even", drawn_number=4
        )
        
        self.assertEqual(result.status, MatchResult.DRAW)
        self.assertIsNone(result.winner_player_id)
        self.assertEqual(result.scores["P01"], 1)
        self.assertEqual(result.scores["P02"], 1)
        self.assertIn("correct", result.reason.lower())
    
    def test_determine_winner_draw_both_wrong(self):
        """Test draw when both players are wrong."""
        result = self.game.determine_winner(
            "P01", "P02", "odd", "odd", drawn_number=6
        )
        
        self.assertEqual(result.status, MatchResult.DRAW)
        self.assertIsNone(result.winner_player_id)
        self.assertIn("wrong", result.reason.lower())
    
    def test_determine_winner_random_number(self):
        """Test with random number (no drawn_number specified)."""
        result = self.game.determine_winner(
            "P01", "P02", "even", "odd"
        )
        
        self.assertIn(result.drawn_number, range(1, 11))
        self.assertIn(result.status, [MatchResult.WIN, MatchResult.DRAW])
    
    def test_init_game_state(self):
        """Test initializing game state."""
        state = self.game.init_game_state("R1M1", "P01", "P02")
        
        self.assertEqual(state["match_id"], "R1M1")
        self.assertEqual(state["state"], GameState.WAITING_FOR_PLAYERS.value)
        self.assertIn("P01", state["players"])
        self.assertIn("P02", state["players"])
        self.assertFalse(state["players"]["P01"]["joined"])
    
    def test_create_technical_loss(self):
        """Test creating technical loss result."""
        result = self.game.create_technical_loss(
            "P01", "P02", "P01", "Player P01 timed out"
        )
        
        self.assertEqual(result.status, MatchResult.TECHNICAL_LOSS)
        self.assertEqual(result.winner_player_id, "P02")
        self.assertEqual(result.scores["P02"], 3)
        self.assertEqual(result.scores["P01"], 0)
        self.assertIn("timed out", result.reason)
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = self.game.determine_winner(
            "P01", "P02", "even", "odd", drawn_number=8
        )
        
        result_dict = self.game.result_to_dict(result)
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict["status"], "WIN")
        self.assertEqual(result_dict["winner_player_id"], "P01")
        self.assertEqual(result_dict["drawn_number"], 8)
    
    def test_scoring_constants(self):
        """Test scoring constants."""
        self.assertEqual(self.game.WIN_POINTS, 3)
        self.assertEqual(self.game.DRAW_POINTS, 1)
        self.assertEqual(self.game.LOSS_POINTS, 0)
    
    def test_number_range_constants(self):
        """Test number range constants."""
        self.assertEqual(self.game.MIN_NUMBER, 1)
        self.assertEqual(self.game.MAX_NUMBER, 10)
    
    def test_valid_choices_constant(self):
        """Test valid choices set."""
        self.assertEqual(self.game.VALID_CHOICES, {"even", "odd"})


class TestGameResult(unittest.TestCase):
    """Tests for GameResult dataclass."""
    
    def test_game_result_creation(self):
        """Test creating a GameResult."""
        result = GameResult(
            status=MatchResult.WIN,
            winner_player_id="P01",
            drawn_number=8,
            number_parity="even",
            choices={"P01": "even", "P02": "odd"},
            reason="P01 won",
            scores={"P01": 3, "P02": 0}
        )
        
        self.assertEqual(result.status, MatchResult.WIN)
        self.assertEqual(result.winner_player_id, "P01")
        self.assertEqual(result.drawn_number, 8)


class TestGameState(unittest.TestCase):
    """Tests for GameState enum."""
    
    def test_game_states(self):
        """Test all game states exist."""
        self.assertEqual(GameState.WAITING_FOR_PLAYERS.value, "WAITING_FOR_PLAYERS")
        self.assertEqual(GameState.COLLECTING_CHOICES.value, "COLLECTING_CHOICES")
        self.assertEqual(GameState.DRAWING_NUMBER.value, "DRAWING_NUMBER")
        self.assertEqual(GameState.FINISHED.value, "FINISHED")


class TestMatchResult(unittest.TestCase):
    """Tests for MatchResult enum."""
    
    def test_match_results(self):
        """Test all match results exist."""
        self.assertEqual(MatchResult.WIN.value, "WIN")
        self.assertEqual(MatchResult.DRAW.value, "DRAW")
        self.assertEqual(MatchResult.TECHNICAL_LOSS.value, "TECHNICAL_LOSS")


if __name__ == "__main__":
    unittest.main()

