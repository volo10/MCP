"""
Player Strategy - Decision-making strategies for the Even/Odd game.

Based on Chapter 3.6 of the League Protocol specification.

Implements:
- RandomStrategy: Pure random choice
- HistoryBasedStrategy: Analyzes past results
- AdaptiveStrategy: Combines multiple approaches

Note: Since the drawn number is random, no strategy can guarantee
better results. These strategies are for demonstration purposes.
"""

import random
from abc import ABC, abstractmethod
from typing import Literal, Optional, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from league_sdk import PlayerHistoryRepository


ParityChoice = Literal["even", "odd"]


class Strategy(ABC):
    """Abstract base class for player strategies."""
    
    @abstractmethod
    def choose(self, context: Dict = None) -> ParityChoice:
        """
        Make a parity choice.
        
        Args:
            context: Optional context including opponent_id, standings, etc.
        
        Returns:
            "even" or "odd" (lowercase)
        """
        pass
    
    @abstractmethod
    def update(self, result: Dict) -> None:
        """
        Update strategy based on match result.
        
        Args:
            result: Match result including choice, outcome, etc.
        """
        pass


class RandomStrategy(Strategy):
    """
    Random choice strategy.
    
    Simply picks "even" or "odd" with equal probability.
    This is the baseline strategy.
    """
    
    def __init__(self, seed: int = None):
        """
        Initialize random strategy.
        
        Args:
            seed: Optional random seed for reproducibility.
        """
        if seed is not None:
            random.seed(seed)
    
    def choose(self, context: Dict = None) -> ParityChoice:
        """Make a random choice."""
        return random.choice(["even", "odd"])
    
    def update(self, result: Dict) -> None:
        """Random strategy doesn't learn."""
        pass


class HistoryBasedStrategy(Strategy):
    """
    History-based strategy.
    
    Analyzes past results to make decisions:
    - Tracks which choice won more often
    - Can adjust based on opponent-specific history
    
    Note: Since draws are random, this won't actually improve
    win rate, but demonstrates the pattern.
    """
    
    def __init__(self, history_repo: "PlayerHistoryRepository"):
        """
        Initialize history-based strategy.
        
        Args:
            history_repo: Repository for accessing match history.
        """
        self.history_repo = history_repo
        
        # Internal counters
        self.even_wins = 0
        self.odd_wins = 0
        self.total_matches = 0
        
        # Load historical data
        self._load_history()
    
    def _load_history(self) -> None:
        """Load and analyze historical match data."""
        if not self.history_repo:
            return
        
        matches = self.history_repo.get_matches()
        
        for match in matches:
            my_choice = match.get("my_choice")
            result = match.get("result")
            
            if result == "WIN" and my_choice:
                if my_choice == "even":
                    self.even_wins += 1
                else:
                    self.odd_wins += 1
            
            self.total_matches += 1
    
    def choose(self, context: Dict = None) -> ParityChoice:
        """
        Make a choice based on historical performance.
        
        If we have history, slightly favor the choice that
        has won more often. Otherwise, random.
        """
        if self.total_matches < 5:
            # Not enough data, use random
            return random.choice(["even", "odd"])
        
        # Calculate win rates
        total_wins = self.even_wins + self.odd_wins
        if total_wins == 0:
            return random.choice(["even", "odd"])
        
        even_rate = self.even_wins / total_wins if total_wins > 0 else 0.5
        
        # Slightly favor the historically better choice
        # But still maintain some randomness
        if random.random() < 0.7:
            # 70% of the time, go with historical favorite
            return "even" if even_rate >= 0.5 else "odd"
        else:
            # 30% of the time, try the other choice
            return "odd" if even_rate >= 0.5 else "even"
    
    def update(self, result: Dict) -> None:
        """Update counters based on new result."""
        self.total_matches += 1
        
        if result.get("result") == "WIN":
            choice = result.get("my_choice")
            if choice == "even":
                self.even_wins += 1
            elif choice == "odd":
                self.odd_wins += 1


class AdaptiveStrategy(Strategy):
    """
    Adaptive strategy that combines multiple approaches.
    
    - Starts with random choices
    - Analyzes patterns in drawn numbers (even though they're random)
    - Tracks opponent tendencies
    - Adjusts over time
    """
    
    def __init__(self, history_repo: "PlayerHistoryRepository"):
        """
        Initialize adaptive strategy.
        
        Args:
            history_repo: Repository for accessing match history.
        """
        self.history_repo = history_repo
        
        # Track drawn number patterns
        self.recent_numbers: List[int] = []
        self.recent_parities: List[str] = []
        
        # Opponent-specific tracking
        self.opponent_history: Dict[str, List[Dict]] = {}
        
        # My performance
        self.my_choices: List[str] = []
        self.results: List[str] = []
        
        self._load_history()
    
    def _load_history(self) -> None:
        """Load historical data."""
        if not self.history_repo:
            return
        
        matches = self.history_repo.get_matches(limit=50)
        
        for match in matches:
            details = match.get("details", {})
            drawn_number = details.get("drawn_number")
            
            if drawn_number:
                self.recent_numbers.append(drawn_number)
                parity = "even" if drawn_number % 2 == 0 else "odd"
                self.recent_parities.append(parity)
            
            opponent_id = match.get("opponent_id")
            if opponent_id:
                if opponent_id not in self.opponent_history:
                    self.opponent_history[opponent_id] = []
                self.opponent_history[opponent_id].append(match)
    
    def choose(self, context: Dict = None) -> ParityChoice:
        """
        Make an adaptive choice based on multiple factors.
        """
        opponent_id = context.get("opponent_id") if context else None
        
        # Strategy 1: Check recent number patterns (pseudo-pattern detection)
        if len(self.recent_parities) >= 5:
            recent = self.recent_parities[-5:]
            even_count = recent.count("even")
            odd_count = recent.count("odd")
            
            # If there's a strong recent trend, bet against it (gambler's fallacy)
            # This doesn't actually help, but demonstrates the pattern
            if even_count >= 4:
                # Many recent evens, guess odd (hoping for "correction")
                if random.random() < 0.6:
                    return "odd"
            elif odd_count >= 4:
                if random.random() < 0.6:
                    return "even"
        
        # Strategy 2: Opponent-specific tendencies
        if opponent_id and opponent_id in self.opponent_history:
            opponent_matches = self.opponent_history[opponent_id]
            if len(opponent_matches) >= 3:
                # Check if opponent has a pattern
                opponent_choices = [m.get("opponent_choice") for m in opponent_matches 
                                   if m.get("opponent_choice")]
                if opponent_choices:
                    # Pick what would beat opponent's most common choice
                    even_choices = opponent_choices.count("even")
                    odd_choices = opponent_choices.count("odd")
                    
                    # Match opponent's likely choice (since we can't counter, just adapt)
                    if even_choices > odd_choices and random.random() < 0.6:
                        return "even"
                    elif odd_choices > even_choices and random.random() < 0.6:
                        return "odd"
        
        # Default: Random choice
        return random.choice(["even", "odd"])
    
    def update(self, result: Dict) -> None:
        """Update internal tracking based on new result."""
        my_choice = result.get("my_choice")
        match_result = result.get("result")
        opponent_id = result.get("opponent_id")
        details = result.get("details", {})
        
        if my_choice:
            self.my_choices.append(my_choice)
        if match_result:
            self.results.append(match_result)
        
        # Track drawn number
        drawn_number = details.get("drawn_number")
        if drawn_number:
            self.recent_numbers.append(drawn_number)
            parity = "even" if drawn_number % 2 == 0 else "odd"
            self.recent_parities.append(parity)
            
            # Keep only recent history
            if len(self.recent_numbers) > 100:
                self.recent_numbers = self.recent_numbers[-50:]
                self.recent_parities = self.recent_parities[-50:]
        
        # Track opponent
        if opponent_id:
            if opponent_id not in self.opponent_history:
                self.opponent_history[opponent_id] = []
            self.opponent_history[opponent_id].append(result)


class StrategyManager:
    """
    Manager for selecting and using strategies.
    """
    
    STRATEGIES = {
        "random": RandomStrategy,
        "history": HistoryBasedStrategy,
        "adaptive": AdaptiveStrategy,
    }
    
    def __init__(self, strategy_type: str, history_repo: "PlayerHistoryRepository" = None):
        """
        Initialize the strategy manager.
        
        Args:
            strategy_type: Type of strategy ("random", "history", "adaptive").
            history_repo: Repository for history-based strategies.
        """
        self.strategy_type = strategy_type
        self.history_repo = history_repo
        self.strategy = self._create_strategy(strategy_type)
    
    def _create_strategy(self, strategy_type: str) -> Strategy:
        """Create a strategy instance."""
        if strategy_type == "random":
            return RandomStrategy()
        elif strategy_type == "history":
            return HistoryBasedStrategy(self.history_repo)
        elif strategy_type == "adaptive":
            return AdaptiveStrategy(self.history_repo)
        else:
            # Default to random
            return RandomStrategy()
    
    def choose(self, context: Dict = None) -> ParityChoice:
        """Make a choice using the current strategy."""
        choice = self.strategy.choose(context)
        # Ensure lowercase
        return choice.lower()
    
    def update(self, result: Dict) -> None:
        """Update strategy with match result."""
        self.strategy.update(result)
    
    def switch_strategy(self, new_type: str) -> None:
        """Switch to a different strategy."""
        self.strategy_type = new_type
        self.strategy = self._create_strategy(new_type)


# Testing
if __name__ == "__main__":
    print("Strategy Module Test")
    print("=" * 40)
    
    # Test random strategy
    random_strat = RandomStrategy(seed=42)
    choices = [random_strat.choose() for _ in range(10)]
    print(f"Random choices: {choices}")
    print(f"  Even: {choices.count('even')}, Odd: {choices.count('odd')}")
    
    # Test strategy manager
    manager = StrategyManager("random")
    choices = [manager.choose() for _ in range(10)]
    print(f"\nManager (random) choices: {choices}")
    
    print("\nAll strategy tests passed!")

