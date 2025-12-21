"""
League SDK - Python toolkit for the MCP League Protocol.

This SDK provides:
- config_models: Dataclass definitions for configuration
- config_loader: ConfigLoader class for lazy-loading configuration
- repositories: Data repositories for runtime data management
- logger: JsonLogger for structured JSONL logging
"""

from .config_models import (
    NetworkConfig,
    SecurityConfig,
    TimeoutsConfig,
    RetryPolicyConfig,
    SystemConfig,
    RefereeConfig,
    PlayerConfig,
    LeagueManagerConfig,
    AgentsConfig,
    ScoringConfig,
    ParticipantsConfig,
    ScheduleConfig,
    LeagueConfig,
    GameTypeConfig,
    GamesRegistry,
)

from .config_loader import ConfigLoader

from .repositories import (
    StandingsRepository,
    MatchRepository,
    PlayerHistoryRepository,
)

from .logger import JsonLogger

__all__ = [
    # Config Models
    "NetworkConfig",
    "SecurityConfig",
    "TimeoutsConfig",
    "RetryPolicyConfig",
    "SystemConfig",
    "RefereeConfig",
    "PlayerConfig",
    "LeagueManagerConfig",
    "AgentsConfig",
    "ScoringConfig",
    "ParticipantsConfig",
    "ScheduleConfig",
    "LeagueConfig",
    "GameTypeConfig",
    "GamesRegistry",
    # Config Loader
    "ConfigLoader",
    # Repositories
    "StandingsRepository",
    "MatchRepository",
    "PlayerHistoryRepository",
    # Logger
    "JsonLogger",
]

__version__ = "1.0.0"

