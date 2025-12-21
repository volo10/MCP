"""
Configuration Models - Dataclass definitions for league configuration.

Based on Chapter 10 of the League Protocol specification.
Uses Python dataclasses for type-safe configuration handling.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# =============================================================================
# System Configuration Models (config/system.json)
# =============================================================================

@dataclass
class NetworkConfig:
    """Network configuration for the league system."""
    base_host: str
    default_league_manager_port: int
    default_referee_port_range: List[int]
    default_player_port_range: List[int]


@dataclass
class SecurityConfig:
    """Security settings including authentication tokens."""
    enable_auth_tokens: bool
    token_length: int
    token_ttl_hours: int


@dataclass
class TimeoutsConfig:
    """Timeout configuration for various operations."""
    register_referee_timeout_sec: int
    register_player_timeout_sec: int
    game_join_ack_timeout_sec: int
    move_timeout_sec: int
    generic_response_timeout_sec: int


@dataclass
class RetryPolicyConfig:
    """Retry policy configuration for failed operations."""
    max_retries: int
    backoff_strategy: str  # "exponential" or "linear"
    initial_delay_sec: float = 1.0


@dataclass
class SystemConfig:
    """Global system configuration (config/system.json)."""
    schema_version: str
    system_id: str
    protocol_version: str
    default_league_id: str
    network: NetworkConfig
    security: SecurityConfig
    timeouts: TimeoutsConfig
    retry_policy: RetryPolicyConfig


# =============================================================================
# Agent Configuration Models (config/agents/agents_config.json)
# =============================================================================

@dataclass
class RefereeConfig:
    """Configuration for a referee agent."""
    referee_id: str
    display_name: str
    endpoint: str
    version: str
    game_types: List[str]
    max_concurrent_matches: int
    active: bool = True


@dataclass
class PlayerConfig:
    """Configuration for a player agent."""
    player_id: str
    display_name: str
    version: str
    preferred_leagues: List[str]
    game_types: List[str]
    default_endpoint: str
    active: bool = True


@dataclass
class LeagueManagerConfig:
    """Configuration for the league manager."""
    endpoint: str
    version: str
    max_concurrent_leagues: int


@dataclass
class AgentsConfig:
    """Registry of all agents in the system."""
    schema_version: str
    league_manager: LeagueManagerConfig
    referees: List[RefereeConfig]
    players: List[PlayerConfig]


# =============================================================================
# League Configuration Models (config/leagues/<league_id>.json)
# =============================================================================

@dataclass
class ScoringConfig:
    """Scoring rules for a league."""
    win_points: int
    draw_points: int
    loss_points: int
    technical_loss_points: int
    tiebreakers: List[str]


@dataclass
class ParticipantsConfig:
    """Participant constraints for a league."""
    min_players: int
    max_players: int
    min_referees: int = 1


@dataclass
class ScheduleConfig:
    """Schedule configuration for a league."""
    format: str  # "round_robin", "knockout", etc.
    matches_per_round: int
    max_rounds: Optional[int] = None


@dataclass
class LeagueConfig:
    """Configuration for a specific league."""
    schema_version: str
    league_id: str
    display_name: str
    game_type: str
    status: str  # "PENDING", "ACTIVE", "COMPLETED"
    scoring: ScoringConfig
    participants: ParticipantsConfig
    schedule: ScheduleConfig


# =============================================================================
# Games Registry Models (config/games/games_registry.json)
# =============================================================================

@dataclass
class GameTypeConfig:
    """Configuration for a specific game type."""
    game_type: str
    display_name: str
    rules_module: str
    move_types: List[str]
    valid_choices: dict
    min_players: int
    max_players: int
    max_round_time_sec: int


@dataclass
class GamesRegistry:
    """Registry of all supported game types."""
    schema_version: str
    games: List[GameTypeConfig]

