"""
Configuration Loader - Lazy-loading configuration with caching.

Based on Chapter 10 of the League Protocol specification.
Implements the Lazy Loading pattern with caching for efficient configuration access.
"""

import json
from pathlib import Path
from typing import Dict, Optional

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

# Default paths
CONFIG_ROOT = Path(__file__).parent.parent / "config"


class ConfigLoader:
    """
    Configuration loader with lazy loading and caching.
    
    Implements the Lazy Loading pattern - configuration files are only
    loaded when first accessed and then cached for subsequent requests.
    """
    
    def __init__(self, root: Path = CONFIG_ROOT):
        """
        Initialize the ConfigLoader.
        
        Args:
            root: Root directory for configuration files.
                  Defaults to SHARED/config/
        """
        self.root = Path(root)
        self._system: Optional[SystemConfig] = None
        self._agents: Optional[AgentsConfig] = None
        self._leagues: Dict[str, LeagueConfig] = {}
        self._games_registry: Optional[GamesRegistry] = None
    
    # =========================================================================
    # Primary Loading Methods
    # =========================================================================
    
    def load_system(self) -> SystemConfig:
        """
        Load global system configuration.
        
        Returns:
            SystemConfig: The global system configuration.
        
        Raises:
            FileNotFoundError: If system.json doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        if self._system is not None:
            return self._system
        
        path = self.root / "system.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        
        self._system = SystemConfig(
            schema_version=data["schema_version"],
            system_id=data["system_id"],
            protocol_version=data["protocol_version"],
            default_league_id=data["default_league_id"],
            network=NetworkConfig(
                base_host=data["network"]["base_host"],
                default_league_manager_port=data["network"]["default_league_manager_port"],
                default_referee_port_range=data["network"]["default_referee_port_range"],
                default_player_port_range=data["network"]["default_player_port_range"],
            ),
            security=SecurityConfig(
                enable_auth_tokens=data["security"]["enable_auth_tokens"],
                token_length=data["security"]["token_length"],
                token_ttl_hours=data["security"]["token_ttl_hours"],
            ),
            timeouts=TimeoutsConfig(
                register_referee_timeout_sec=data["timeouts"]["register_referee_timeout_sec"],
                register_player_timeout_sec=data["timeouts"]["register_player_timeout_sec"],
                game_join_ack_timeout_sec=data["timeouts"]["game_join_ack_timeout_sec"],
                move_timeout_sec=data["timeouts"]["move_timeout_sec"],
                generic_response_timeout_sec=data["timeouts"]["generic_response_timeout_sec"],
            ),
            retry_policy=RetryPolicyConfig(
                max_retries=data["retry_policy"]["max_retries"],
                backoff_strategy=data["retry_policy"]["backoff_strategy"],
                initial_delay_sec=data["retry_policy"].get("initial_delay_sec", 1.0),
            ),
        )
        
        return self._system
    
    def load_agents(self) -> AgentsConfig:
        """
        Load agents configuration (all referees and players).
        
        Returns:
            AgentsConfig: Registry of all agents.
        
        Raises:
            FileNotFoundError: If agents_config.json doesn't exist.
        """
        if self._agents is not None:
            return self._agents
        
        path = self.root / "agents" / "agents_config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        
        referees = [
            RefereeConfig(
                referee_id=ref["referee_id"],
                display_name=ref["display_name"],
                endpoint=ref["endpoint"],
                version=ref["version"],
                game_types=ref["game_types"],
                max_concurrent_matches=ref["max_concurrent_matches"],
                active=ref.get("active", True),
            )
            for ref in data.get("referees", [])
        ]
        
        players = [
            PlayerConfig(
                player_id=player["player_id"],
                display_name=player["display_name"],
                version=player["version"],
                preferred_leagues=player.get("preferred_leagues", []),
                game_types=player["game_types"],
                default_endpoint=player["default_endpoint"],
                active=player.get("active", True),
            )
            for player in data.get("players", [])
        ]
        
        league_manager = LeagueManagerConfig(
            endpoint=data["league_manager"]["endpoint"],
            version=data["league_manager"]["version"],
            max_concurrent_leagues=data["league_manager"]["max_concurrent_leagues"],
        )
        
        self._agents = AgentsConfig(
            schema_version=data["schema_version"],
            league_manager=league_manager,
            referees=referees,
            players=players,
        )
        
        return self._agents
    
    def load_league(self, league_id: str) -> LeagueConfig:
        """
        Load configuration for a specific league.
        
        Args:
            league_id: The unique identifier for the league.
        
        Returns:
            LeagueConfig: Configuration for the specified league.
        
        Raises:
            FileNotFoundError: If the league config file doesn't exist.
        """
        if league_id in self._leagues:
            return self._leagues[league_id]
        
        path = self.root / "leagues" / f"{league_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        
        league_config = LeagueConfig(
            schema_version=data["schema_version"],
            league_id=data["league_id"],
            display_name=data["display_name"],
            game_type=data["game_type"],
            status=data["status"],
            scoring=ScoringConfig(
                win_points=data["scoring"]["win_points"],
                draw_points=data["scoring"]["draw_points"],
                loss_points=data["scoring"]["loss_points"],
                technical_loss_points=data["scoring"].get("technical_loss_points", 0),
                tiebreakers=data["scoring"].get("tiebreakers", ["points", "wins"]),
            ),
            participants=ParticipantsConfig(
                min_players=data["participants"]["min_players"],
                max_players=data["participants"]["max_players"],
                min_referees=data["participants"].get("min_referees", 1),
            ),
            schedule=ScheduleConfig(
                format=data["schedule"]["format"],
                matches_per_round=data["schedule"]["matches_per_round"],
                max_rounds=data["schedule"].get("max_rounds"),
            ),
        )
        
        self._leagues[league_id] = league_config
        return league_config
    
    def load_games_registry(self) -> GamesRegistry:
        """
        Load the games registry (all supported game types).
        
        Returns:
            GamesRegistry: Registry of all supported game types.
        """
        if self._games_registry is not None:
            return self._games_registry
        
        path = self.root / "games" / "games_registry.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        
        games = [
            GameTypeConfig(
                game_type=game["game_type"],
                display_name=game["display_name"],
                rules_module=game["rules_module"],
                move_types=game["move_types"],
                valid_choices=game["valid_choices"],
                min_players=game["min_players"],
                max_players=game["max_players"],
                max_round_time_sec=game["max_round_time_sec"],
            )
            for game in data.get("games", [])
        ]
        
        self._games_registry = GamesRegistry(
            schema_version=data["schema_version"],
            games=games,
        )
        
        return self._games_registry
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def get_referee_by_id(self, referee_id: str) -> RefereeConfig:
        """
        Get a referee configuration by ID.
        
        Args:
            referee_id: The referee's unique identifier.
        
        Returns:
            RefereeConfig: The referee's configuration.
        
        Raises:
            ValueError: If the referee is not found.
        """
        agents = self.load_agents()
        for ref in agents.referees:
            if ref.referee_id == referee_id:
                return ref
        raise ValueError(f"Referee not found: {referee_id}")
    
    def get_player_by_id(self, player_id: str) -> PlayerConfig:
        """
        Get a player configuration by ID.
        
        Args:
            player_id: The player's unique identifier.
        
        Returns:
            PlayerConfig: The player's configuration.
        
        Raises:
            ValueError: If the player is not found.
        """
        agents = self.load_agents()
        for player in agents.players:
            if player.player_id == player_id:
                return player
        raise ValueError(f"Player not found: {player_id}")
    
    def get_active_referees(self) -> list[RefereeConfig]:
        """Get all active referees."""
        agents = self.load_agents()
        return [ref for ref in agents.referees if ref.active]
    
    def get_active_players(self) -> list[PlayerConfig]:
        """Get all active players."""
        agents = self.load_agents()
        return [player for player in agents.players if player.active]
    
    def get_game_type(self, game_type: str) -> GameTypeConfig:
        """
        Get a game type configuration.
        
        Args:
            game_type: The game type identifier.
        
        Returns:
            GameTypeConfig: The game type configuration.
        
        Raises:
            ValueError: If the game type is not found.
        """
        registry = self.load_games_registry()
        for game in registry.games:
            if game.game_type == game_type:
                return game
        raise ValueError(f"Game type not found: {game_type}")
    
    # =========================================================================
    # Cache Management
    # =========================================================================
    
    def clear_cache(self) -> None:
        """Clear all cached configurations."""
        self._system = None
        self._agents = None
        self._leagues.clear()
        self._games_registry = None
    
    def reload_system(self) -> SystemConfig:
        """Force reload system configuration."""
        self._system = None
        return self.load_system()
    
    def reload_agents(self) -> AgentsConfig:
        """Force reload agents configuration."""
        self._agents = None
        return self.load_agents()
    
    def reload_league(self, league_id: str) -> LeagueConfig:
        """Force reload a specific league configuration."""
        if league_id in self._leagues:
            del self._leagues[league_id]
        return self.load_league(league_id)

