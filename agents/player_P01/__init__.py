"""
Player Agent Package.

Participates in matches for the MCP League Protocol.
"""

from .strategy import (
    Strategy,
    RandomStrategy,
    HistoryBasedStrategy,
    AdaptiveStrategy,
    StrategyManager,
)

from .resilience import (
    RetryClient,
    CircuitBreaker,
    ResilientClient,
    ErrorCode,
    RetryableError,
)

__all__ = [
    # Strategies
    "Strategy",
    "RandomStrategy",
    "HistoryBasedStrategy",
    "AdaptiveStrategy",
    "StrategyManager",
    # Resilience
    "RetryClient",
    "CircuitBreaker",
    "ResilientClient",
    "ErrorCode",
    "RetryableError",
]

__version__ = "1.0.0"

