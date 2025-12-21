"""
Unit tests for strategy.py (Player strategies)
"""

import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "player_P01"))

import unittest
from strategy import (
    Strategy,
    RandomStrategy,
    HistoryBasedStrategy,
    AdaptiveStrategy,
    StrategyManager,
)


class TestRandomStrategy(unittest.TestCase):
    """Tests for RandomStrategy class."""
    
    def test_choose_valid_output(self):
        """Test that choose returns valid choice."""
        strategy = RandomStrategy(seed=42)
        
        for _ in range(100):
            choice = strategy.choose()
            self.assertIn(choice, ["even", "odd"])
    
    def test_choose_with_context(self):
        """Test choosing with context."""
        strategy = RandomStrategy(seed=42)
        
        choice = strategy.choose({"opponent_id": "P02"})
        self.assertIn(choice, ["even", "odd"])
    
    def test_choose_distribution(self):
        """Test that choices are roughly 50/50."""
        strategy = RandomStrategy()  # No seed for random
        
        choices = [strategy.choose() for _ in range(1000)]
        even_count = choices.count("even")
        odd_count = choices.count("odd")
        
        # Should be roughly 50/50 (allow 40-60 range)
        self.assertGreater(even_count, 350)
        self.assertLess(even_count, 650)
    
    def test_update_does_nothing(self):
        """Test that update doesn't change behavior."""
        strategy = RandomStrategy(seed=42)
        
        choice1 = strategy.choose()
        strategy.update({"result": "WIN", "my_choice": "even"})
        
        # Reset seed and verify same choice
        strategy = RandomStrategy(seed=42)
        choice2 = strategy.choose()
        
        self.assertEqual(choice1, choice2)
    
    def test_reproducibility_with_seed(self):
        """Test that same seed produces same sequence."""
        strategy1 = RandomStrategy(seed=123)
        strategy2 = RandomStrategy(seed=123)
        
        choices1 = [strategy1.choose() for _ in range(10)]
        choices2 = [strategy2.choose() for _ in range(10)]
        
        self.assertEqual(choices1, choices2)


class TestHistoryBasedStrategy(unittest.TestCase):
    """Tests for HistoryBasedStrategy class."""
    
    def test_choose_without_history(self):
        """Test choosing without history (should be random)."""
        strategy = HistoryBasedStrategy(None)
        
        choice = strategy.choose()
        self.assertIn(choice, ["even", "odd"])
    
    def test_choose_with_limited_history(self):
        """Test choosing with less than 5 matches."""
        strategy = HistoryBasedStrategy(None)
        strategy.total_matches = 3
        strategy.even_wins = 2
        strategy.odd_wins = 1
        
        # With < 5 matches, should still be random
        choice = strategy.choose()
        self.assertIn(choice, ["even", "odd"])
    
    def test_update_win(self):
        """Test updating strategy with a win."""
        strategy = HistoryBasedStrategy(None)
        
        strategy.update({"result": "WIN", "my_choice": "even"})
        
        self.assertEqual(strategy.total_matches, 1)
        self.assertEqual(strategy.even_wins, 1)
        self.assertEqual(strategy.odd_wins, 0)
    
    def test_update_loss(self):
        """Test updating strategy with a loss."""
        strategy = HistoryBasedStrategy(None)
        
        strategy.update({"result": "LOSS", "my_choice": "odd"})
        
        self.assertEqual(strategy.total_matches, 1)
        self.assertEqual(strategy.even_wins, 0)
        self.assertEqual(strategy.odd_wins, 0)


class TestAdaptiveStrategy(unittest.TestCase):
    """Tests for AdaptiveStrategy class."""
    
    def test_choose_default(self):
        """Test default choice is valid."""
        strategy = AdaptiveStrategy(None)
        
        choice = strategy.choose()
        self.assertIn(choice, ["even", "odd"])
    
    def test_choose_with_context(self):
        """Test choosing with opponent context."""
        strategy = AdaptiveStrategy(None)
        
        choice = strategy.choose({"opponent_id": "P02"})
        self.assertIn(choice, ["even", "odd"])
    
    def test_update_tracks_numbers(self):
        """Test that update tracks drawn numbers."""
        strategy = AdaptiveStrategy(None)
        
        strategy.update({
            "result": "WIN",
            "my_choice": "even",
            "opponent_id": "P02",
            "details": {"drawn_number": 8}
        })
        
        self.assertEqual(len(strategy.recent_numbers), 1)
        self.assertEqual(strategy.recent_numbers[0], 8)
        self.assertEqual(strategy.recent_parities[0], "even")
    
    def test_update_tracks_opponent(self):
        """Test that update tracks opponent history."""
        strategy = AdaptiveStrategy(None)
        
        strategy.update({
            "result": "WIN",
            "my_choice": "even",
            "opponent_id": "P02",
            "details": {}
        })
        
        self.assertIn("P02", strategy.opponent_history)
        self.assertEqual(len(strategy.opponent_history["P02"]), 1)


class TestStrategyManager(unittest.TestCase):
    """Tests for StrategyManager class."""
    
    def test_create_random_strategy(self):
        """Test creating random strategy."""
        manager = StrategyManager("random")
        
        self.assertEqual(manager.strategy_type, "random")
        self.assertIsInstance(manager.strategy, RandomStrategy)
    
    def test_create_history_strategy(self):
        """Test creating history-based strategy."""
        manager = StrategyManager("history")
        
        self.assertEqual(manager.strategy_type, "history")
        self.assertIsInstance(manager.strategy, HistoryBasedStrategy)
    
    def test_create_adaptive_strategy(self):
        """Test creating adaptive strategy."""
        manager = StrategyManager("adaptive")
        
        self.assertEqual(manager.strategy_type, "adaptive")
        self.assertIsInstance(manager.strategy, AdaptiveStrategy)
    
    def test_create_unknown_strategy_defaults_to_random(self):
        """Test that unknown strategy defaults to random."""
        manager = StrategyManager("unknown")
        
        self.assertIsInstance(manager.strategy, RandomStrategy)
    
    def test_choose_returns_lowercase(self):
        """Test that choose always returns lowercase."""
        manager = StrategyManager("random")
        
        for _ in range(100):
            choice = manager.choose()
            self.assertEqual(choice, choice.lower())
    
    def test_choose_with_context(self):
        """Test choosing with context."""
        manager = StrategyManager("random")
        
        choice = manager.choose({"opponent_id": "P02", "round_id": 1})
        self.assertIn(choice, ["even", "odd"])
    
    def test_update(self):
        """Test updating strategy."""
        manager = StrategyManager("adaptive")
        
        # Should not raise
        manager.update({
            "result": "WIN",
            "my_choice": "even",
            "opponent_id": "P02"
        })
    
    def test_switch_strategy(self):
        """Test switching strategy."""
        manager = StrategyManager("random")
        self.assertIsInstance(manager.strategy, RandomStrategy)
        
        manager.switch_strategy("adaptive")
        self.assertIsInstance(manager.strategy, AdaptiveStrategy)
        self.assertEqual(manager.strategy_type, "adaptive")


class TestStrategyIntegration(unittest.TestCase):
    """Integration tests for strategies."""
    
    def test_all_strategies_work(self):
        """Test that all strategies produce valid choices."""
        strategies = ["random", "history", "adaptive"]
        
        for strategy_type in strategies:
            manager = StrategyManager(strategy_type)
            
            for _ in range(10):
                choice = manager.choose({"opponent_id": "P02"})
                self.assertIn(choice, ["even", "odd"],
                             f"Strategy {strategy_type} returned invalid choice")
    
    def test_strategy_update_cycle(self):
        """Test complete update cycle."""
        manager = StrategyManager("adaptive")
        
        for i in range(5):
            choice = manager.choose({"opponent_id": "P02"})
            
            result = {
                "result": "WIN" if i % 2 == 0 else "LOSS",
                "my_choice": choice,
                "opponent_id": "P02",
                "details": {"drawn_number": i + 1}
            }
            
            manager.update(result)
        
        # Should still work after updates
        choice = manager.choose()
        self.assertIn(choice, ["even", "odd"])


if __name__ == "__main__":
    unittest.main()

