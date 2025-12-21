"""
Even/Odd Game Logic - Game rules implementation.

Based on Chapter 3 of the League Protocol specification.

Game Rules:
1. Two players each choose "even" or "odd"
2. A random number from 1-10 is drawn
3. If the number is even, players who chose "even" win
4. If the number is odd, players who chose "odd" win
5. If both players chose correctly or both wrong, it's a draw

Scoring:
- Win: 3 points
- Draw: 1 point each
- Loss: 0 points
"""

import random
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Literal
from enum import Enum


class GameState(Enum):
    """Possible states of a match."""
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    COLLECTING_CHOICES = "COLLECTING_CHOICES"
    DRAWING_NUMBER = "DRAWING_NUMBER"
    FINISHED = "FINISHED"


class MatchResult(Enum):
    """Possible match outcomes."""
    WIN = "WIN"
    DRAW = "DRAW"
    TECHNICAL_LOSS = "TECHNICAL_LOSS"


ParityChoice = Literal["even", "odd"]


@dataclass
class GameResult:
    """Result of a single game."""
    status: MatchResult
    winner_player_id: Optional[str]
    drawn_number: int
    number_parity: ParityChoice
    choices: Dict[str, ParityChoice]
    reason: str
    scores: Dict[str, int]


class EvenOddGame:
    """
    Even/Odd game logic implementation.
    
    This class provides methods to:
    - Initialize game state
    - Validate player choices
    - Draw random numbers
    - Determine winners
    """
    
    VALID_CHOICES = {"even", "odd"}
    MIN_NUMBER = 1
    MAX_NUMBER = 10
    
    # Scoring
    WIN_POINTS = 3
    DRAW_POINTS = 1
    LOSS_POINTS = 0
    
    def __init__(self, seed: int = None):
        """
        Initialize the game logic.
        
        Args:
            seed: Optional random seed for reproducibility.
        """
        if seed is not None:
            random.seed(seed)
    
    def init_game_state(self, match_id: str, player_a: str, player_b: str) -> dict:
        """
        Initialize the state for a new game.
        
        Args:
            match_id: Unique identifier for the match.
            player_a: First player's ID.
            player_b: Second player's ID.
        
        Returns:
            Initial game state dictionary.
        """
        return {
            "match_id": match_id,
            "state": GameState.WAITING_FOR_PLAYERS.value,
            "players": {
                player_a: {"joined": False, "choice": None},
                player_b: {"joined": False, "choice": None}
            },
            "drawn_number": None,
            "result": None
        }
    
    def validate_choice(self, choice: str) -> bool:
        """
        Validate that a choice is valid ("even" or "odd").
        
        Args:
            choice: The player's choice.
        
        Returns:
            True if valid, False otherwise.
        """
        return choice.lower() in self.VALID_CHOICES
    
    def normalize_choice(self, choice: str) -> ParityChoice:
        """
        Normalize a choice to lowercase.
        
        Args:
            choice: The player's choice.
        
        Returns:
            Normalized choice.
        
        Raises:
            ValueError: If choice is invalid.
        """
        normalized = choice.lower()
        if normalized not in self.VALID_CHOICES:
            raise ValueError(f"Invalid choice: {choice}. Must be 'even' or 'odd'.")
        return normalized
    
    def draw_number(self) -> int:
        """
        Draw a random number between 1 and 10.
        
        Returns:
            Random integer from 1 to 10.
        """
        return random.randint(self.MIN_NUMBER, self.MAX_NUMBER)
    
    def get_parity(self, number: int) -> ParityChoice:
        """
        Determine if a number is even or odd.
        
        Args:
            number: The number to check.
        
        Returns:
            "even" or "odd"
        """
        return "even" if number % 2 == 0 else "odd"
    
    def determine_winner(
        self,
        player_a: str,
        player_b: str,
        choice_a: ParityChoice,
        choice_b: ParityChoice,
        drawn_number: int = None
    ) -> GameResult:
        """
        Determine the winner of a match.
        
        Args:
            player_a: First player's ID.
            player_b: Second player's ID.
            choice_a: First player's choice.
            choice_b: Second player's choice.
            drawn_number: Optional pre-drawn number (draws if None).
        
        Returns:
            GameResult with winner information.
        """
        # Draw number if not provided
        if drawn_number is None:
            drawn_number = self.draw_number()
        
        number_parity = self.get_parity(drawn_number)
        
        # Determine who guessed correctly
        a_correct = choice_a == number_parity
        b_correct = choice_b == number_parity
        
        choices = {player_a: choice_a, player_b: choice_b}
        
        if a_correct and not b_correct:
            # Player A wins
            return GameResult(
                status=MatchResult.WIN,
                winner_player_id=player_a,
                drawn_number=drawn_number,
                number_parity=number_parity,
                choices=choices,
                reason=f"{player_a} chose {choice_a}, number was {drawn_number} ({number_parity})",
                scores={player_a: self.WIN_POINTS, player_b: self.LOSS_POINTS}
            )
        
        elif b_correct and not a_correct:
            # Player B wins
            return GameResult(
                status=MatchResult.WIN,
                winner_player_id=player_b,
                drawn_number=drawn_number,
                number_parity=number_parity,
                choices=choices,
                reason=f"{player_b} chose {choice_b}, number was {drawn_number} ({number_parity})",
                scores={player_a: self.LOSS_POINTS, player_b: self.WIN_POINTS}
            )
        
        else:
            # Draw (both correct or both wrong)
            if a_correct:
                reason = f"Both chose correctly ({number_parity}), number was {drawn_number}"
            else:
                reason = f"Both guessed wrong, number was {drawn_number} ({number_parity})"
            
            return GameResult(
                status=MatchResult.DRAW,
                winner_player_id=None,
                drawn_number=drawn_number,
                number_parity=number_parity,
                choices=choices,
                reason=reason,
                scores={player_a: self.DRAW_POINTS, player_b: self.DRAW_POINTS}
            )
    
    def create_technical_loss(
        self,
        player_a: str,
        player_b: str,
        losing_player: str,
        reason: str
    ) -> GameResult:
        """
        Create a technical loss result (e.g., timeout).
        
        Args:
            player_a: First player's ID.
            player_b: Second player's ID.
            losing_player: The player who loses technically.
            reason: Reason for the technical loss.
        
        Returns:
            GameResult with technical loss.
        """
        winner = player_b if losing_player == player_a else player_a
        
        return GameResult(
            status=MatchResult.TECHNICAL_LOSS,
            winner_player_id=winner,
            drawn_number=0,
            number_parity="even",
            choices={player_a: None, player_b: None},
            reason=reason,
            scores={winner: self.WIN_POINTS, losing_player: self.LOSS_POINTS}
        )
    
    def result_to_dict(self, result: GameResult) -> dict:
        """
        Convert a GameResult to a dictionary for JSON serialization.
        
        Args:
            result: The game result.
        
        Returns:
            Dictionary representation.
        """
        return {
            "status": result.status.value,
            "winner_player_id": result.winner_player_id,
            "drawn_number": result.drawn_number,
            "number_parity": result.number_parity,
            "choices": result.choices,
            "reason": result.reason,
            "scores": result.scores
        }


# Testing
if __name__ == "__main__":
    game = EvenOddGame(seed=42)
    
    print("Even/Odd Game Logic Test")
    print("=" * 40)
    
    # Test scenarios
    test_cases = [
        ("P01", "P02", "even", "odd", 8),   # P01 wins (8 is even)
        ("P01", "P02", "even", "odd", 7),   # P02 wins (7 is odd)
        ("P01", "P02", "even", "even", 4),  # Draw (both correct)
        ("P01", "P02", "odd", "odd", 6),    # Draw (both wrong)
    ]
    
    for p1, p2, c1, c2, num in test_cases:
        result = game.determine_winner(p1, p2, c1, c2, num)
        print(f"\n{p1}:{c1} vs {p2}:{c2}, number={num}")
        print(f"  Result: {result.status.value}")
        print(f"  Winner: {result.winner_player_id}")
        print(f"  Reason: {result.reason}")
        print(f"  Scores: {result.scores}")
    
    # Test random draw
    print("\n" + "=" * 40)
    print("Random number draws:")
    for _ in range(5):
        num = game.draw_number()
        print(f"  Drew {num} ({game.get_parity(num)})")

