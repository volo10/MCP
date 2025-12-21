"""
Referee Agent Package.

Manages individual matches for the MCP League Protocol.
"""

from .game_logic import EvenOddGame, GameState, MatchResult, GameResult

__all__ = ["EvenOddGame", "GameState", "MatchResult", "GameResult"]

