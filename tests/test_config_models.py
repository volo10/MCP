"""
Unit tests for config_models.py
"""

import sys
from pathlib import Path

# Add SHARED to path
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

import unittest
from league_sdk.config_models import (
    NetworkConfig,
    SecurityConfig,
    TimeoutsConfig,
    RetryPolicyConfig,
    SystemConfig,
    RefereeConfig,
    PlayerConfig,
    ScoringConfig,
    LeagueConfig,
    ParticipantsConfig,
    ScheduleConfig,
)


class TestNetworkConfig(unittest.TestCase):
    """Tests for NetworkConfig dataclass."""
    
    def test_create_network_config(self):
        """Test creating a NetworkConfig instance."""
        config = NetworkConfig(
            base_host="localhost",
            default_league_manager_port=8000,
            default_referee_port_range=[8001, 8010],
            default_player_port_range=[8101, 8200]
        )
        
        self.assertEqual(config.base_host, "localhost")
        self.assertEqual(config.default_league_manager_port, 8000)
        self.assertEqual(config.default_referee_port_range, [8001, 8010])
        self.assertEqual(config.default_player_port_range, [8101, 8200])
    
    def test_network_config_immutable_access(self):
        """Test that config attributes are accessible."""
        config = NetworkConfig(
            base_host="127.0.0.1",
            default_league_manager_port=9000,
            default_referee_port_range=[9001, 9010],
            default_player_port_range=[9101, 9200]
        )
        
        self.assertIsInstance(config.default_referee_port_range, list)
        self.assertEqual(len(config.default_player_port_range), 2)


class TestSecurityConfig(unittest.TestCase):
    """Tests for SecurityConfig dataclass."""
    
    def test_create_security_config(self):
        """Test creating a SecurityConfig instance."""
        config = SecurityConfig(
            enable_auth_tokens=True,
            token_length=32,
            token_ttl_hours=24
        )
        
        self.assertTrue(config.enable_auth_tokens)
        self.assertEqual(config.token_length, 32)
        self.assertEqual(config.token_ttl_hours, 24)
    
    def test_security_config_disabled_auth(self):
        """Test config with auth disabled."""
        config = SecurityConfig(
            enable_auth_tokens=False,
            token_length=0,
            token_ttl_hours=0
        )
        
        self.assertFalse(config.enable_auth_tokens)


class TestTimeoutsConfig(unittest.TestCase):
    """Tests for TimeoutsConfig dataclass."""
    
    def test_create_timeouts_config(self):
        """Test creating a TimeoutsConfig instance."""
        config = TimeoutsConfig(
            register_referee_timeout_sec=10,
            register_player_timeout_sec=10,
            game_join_ack_timeout_sec=5,
            move_timeout_sec=30,
            generic_response_timeout_sec=10
        )
        
        self.assertEqual(config.move_timeout_sec, 30)
        self.assertEqual(config.game_join_ack_timeout_sec, 5)


class TestRetryPolicyConfig(unittest.TestCase):
    """Tests for RetryPolicyConfig dataclass."""
    
    def test_exponential_backoff(self):
        """Test exponential backoff configuration."""
        config = RetryPolicyConfig(
            max_retries=3,
            backoff_strategy="exponential",
            initial_delay_sec=1.0
        )
        
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.backoff_strategy, "exponential")
    
    def test_linear_backoff(self):
        """Test linear backoff configuration."""
        config = RetryPolicyConfig(
            max_retries=5,
            backoff_strategy="linear",
            initial_delay_sec=2.0
        )
        
        self.assertEqual(config.backoff_strategy, "linear")
        self.assertEqual(config.initial_delay_sec, 2.0)


class TestRefereeConfig(unittest.TestCase):
    """Tests for RefereeConfig dataclass."""
    
    def test_create_referee_config(self):
        """Test creating a RefereeConfig instance."""
        config = RefereeConfig(
            referee_id="REF01",
            display_name="Referee Alpha",
            endpoint="http://localhost:8001/mcp",
            version="1.0.0",
            game_types=["even_odd"],
            max_concurrent_matches=2,
            active=True
        )
        
        self.assertEqual(config.referee_id, "REF01")
        self.assertEqual(config.display_name, "Referee Alpha")
        self.assertIn("even_odd", config.game_types)
        self.assertTrue(config.active)
    
    def test_referee_default_active(self):
        """Test that active defaults to True."""
        config = RefereeConfig(
            referee_id="REF02",
            display_name="Referee Beta",
            endpoint="http://localhost:8002/mcp",
            version="1.0.0",
            game_types=["even_odd"],
            max_concurrent_matches=1
        )
        
        self.assertTrue(config.active)


class TestPlayerConfig(unittest.TestCase):
    """Tests for PlayerConfig dataclass."""
    
    def test_create_player_config(self):
        """Test creating a PlayerConfig instance."""
        config = PlayerConfig(
            player_id="P01",
            display_name="Agent Alpha",
            version="1.0.0",
            preferred_leagues=["league_2025"],
            game_types=["even_odd"],
            default_endpoint="http://localhost:8101/mcp",
            active=True
        )
        
        self.assertEqual(config.player_id, "P01")
        self.assertEqual(config.display_name, "Agent Alpha")
        self.assertIn("league_2025", config.preferred_leagues)


class TestScoringConfig(unittest.TestCase):
    """Tests for ScoringConfig dataclass."""
    
    def test_create_scoring_config(self):
        """Test creating a ScoringConfig instance."""
        config = ScoringConfig(
            win_points=3,
            draw_points=1,
            loss_points=0,
            technical_loss_points=0,
            tiebreakers=["points", "wins", "draws"]
        )
        
        self.assertEqual(config.win_points, 3)
        self.assertEqual(config.draw_points, 1)
        self.assertEqual(config.loss_points, 0)
        self.assertEqual(len(config.tiebreakers), 3)
    
    def test_scoring_order(self):
        """Test that win > draw > loss."""
        config = ScoringConfig(
            win_points=3,
            draw_points=1,
            loss_points=0,
            technical_loss_points=0,
            tiebreakers=[]
        )
        
        self.assertGreater(config.win_points, config.draw_points)
        self.assertGreater(config.draw_points, config.loss_points)


class TestLeagueConfig(unittest.TestCase):
    """Tests for LeagueConfig dataclass."""
    
    def test_create_league_config(self):
        """Test creating a LeagueConfig instance."""
        scoring = ScoringConfig(
            win_points=3,
            draw_points=1,
            loss_points=0,
            technical_loss_points=0,
            tiebreakers=["points"]
        )
        
        participants = ParticipantsConfig(
            min_players=2,
            max_players=100,
            min_referees=1
        )
        
        schedule = ScheduleConfig(
            format="round_robin",
            matches_per_round=2,
            max_rounds=None
        )
        
        config = LeagueConfig(
            schema_version="1.0.0",
            league_id="test_league",
            display_name="Test League",
            game_type="even_odd",
            status="ACTIVE",
            scoring=scoring,
            participants=participants,
            schedule=schedule
        )
        
        self.assertEqual(config.league_id, "test_league")
        self.assertEqual(config.game_type, "even_odd")
        self.assertEqual(config.status, "ACTIVE")
        self.assertEqual(config.scoring.win_points, 3)


if __name__ == "__main__":
    unittest.main()

