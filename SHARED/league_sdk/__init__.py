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

from .parallel import (
    ParallelConfig,
    TaskResult,
    ThreadSafeCounter,
    ThreadSafeDict,
    TaskQueue,
    ParallelExecutor,
    WorkerPool,
    run_in_thread,
    run_in_process,
    parallel_map_cpu,
    parallel_map_io,
    get_cpu_count,
    get_recommended_thread_count,
    get_recommended_process_count,
)

from .mcp_discovery import (
    Tool,
    ToolParameter,
    Resource,
    MCPDiscovery,
    get_player_tools,
    get_referee_tools,
    get_league_manager_tools,
    get_player_resources,
    get_referee_resources,
    get_league_manager_resources,
)

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
    # Parallel Processing
    "ParallelConfig",
    "TaskResult",
    "ThreadSafeCounter",
    "ThreadSafeDict",
    "TaskQueue",
    "ParallelExecutor",
    "WorkerPool",
    "run_in_thread",
    "run_in_process",
    "parallel_map_cpu",
    "parallel_map_io",
    "get_cpu_count",
    "get_recommended_thread_count",
    "get_recommended_process_count",
    # MCP Discovery
    "Tool",
    "ToolParameter",
    "Resource",
    "MCPDiscovery",
    "get_player_tools",
    "get_referee_tools",
    "get_league_manager_tools",
    "get_player_resources",
    "get_referee_resources",
    "get_league_manager_resources",
]

__version__ = "1.0.0"

