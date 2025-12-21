"""
Unit tests for config_loader.py
"""

import sys
from pathlib import Path

# Add SHARED to path
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

import unittest
from league_sdk.config_loader import ConfigLoader


class TestConfigLoader(unittest.TestCase):
    """Tests for ConfigLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loader = ConfigLoader()
    
    def test_load_system_config(self):
        """Test loading system configuration."""
        system = self.loader.load_system()
        
        self.assertEqual(system.protocol_version, "league.v2")
        self.assertIsNotNone(system.network)
        self.assertIsNotNone(system.security)
        self.assertIsNotNone(system.timeouts)
    
    def test_load_system_config_cached(self):
        """Test that system config is cached."""
        system1 = self.loader.load_system()
        system2 = self.loader.load_system()
        
        # Should be same object (cached)
        self.assertIs(system1, system2)
    
    def test_load_agents_config(self):
        """Test loading agents configuration."""
        agents = self.loader.load_agents()
        
        self.assertIsNotNone(agents.league_manager)
        self.assertIsInstance(agents.referees, list)
        self.assertIsInstance(agents.players, list)
        self.assertGreaterEqual(len(agents.referees), 1)
        self.assertGreaterEqual(len(agents.players), 1)
    
    def test_load_agents_config_cached(self):
        """Test that agents config is cached."""
        agents1 = self.loader.load_agents()
        agents2 = self.loader.load_agents()
        
        self.assertIs(agents1, agents2)
    
    def test_load_league_config(self):
        """Test loading league configuration."""
        league = self.loader.load_league("league_2025_even_odd")
        
        self.assertEqual(league.league_id, "league_2025_even_odd")
        self.assertEqual(league.game_type, "even_odd")
        self.assertIsNotNone(league.scoring)
    
    def test_load_league_config_cached(self):
        """Test that league config is cached."""
        league1 = self.loader.load_league("league_2025_even_odd")
        league2 = self.loader.load_league("league_2025_even_odd")
        
        self.assertIs(league1, league2)
    
    def test_load_games_registry(self):
        """Test loading games registry."""
        games = self.loader.load_games_registry()
        
        self.assertIsNotNone(games.games)
        self.assertGreaterEqual(len(games.games), 1)
        
        # Check for even_odd game
        game_types = [g.game_type for g in games.games]
        self.assertIn("even_odd", game_types)
    
    def test_get_referee_by_id(self):
        """Test getting referee by ID."""
        referee = self.loader.get_referee_by_id("REF01")
        
        self.assertEqual(referee.referee_id, "REF01")
        self.assertIsNotNone(referee.endpoint)
    
    def test_get_referee_by_id_not_found(self):
        """Test getting non-existent referee."""
        with self.assertRaises(ValueError) as context:
            self.loader.get_referee_by_id("REF99")
        
        self.assertIn("not found", str(context.exception))
    
    def test_get_player_by_id(self):
        """Test getting player by ID."""
        player = self.loader.get_player_by_id("P01")
        
        self.assertEqual(player.player_id, "P01")
        self.assertIsNotNone(player.default_endpoint)
    
    def test_get_player_by_id_not_found(self):
        """Test getting non-existent player."""
        with self.assertRaises(ValueError) as context:
            self.loader.get_player_by_id("P99")
        
        self.assertIn("not found", str(context.exception))
    
    def test_get_active_referees(self):
        """Test getting active referees."""
        referees = self.loader.get_active_referees()
        
        self.assertIsInstance(referees, list)
        for ref in referees:
            self.assertTrue(ref.active)
    
    def test_get_active_players(self):
        """Test getting active players."""
        players = self.loader.get_active_players()
        
        self.assertIsInstance(players, list)
        for player in players:
            self.assertTrue(player.active)
    
    def test_get_game_type(self):
        """Test getting game type configuration."""
        game = self.loader.get_game_type("even_odd")
        
        self.assertEqual(game.game_type, "even_odd")
        self.assertIn("choose_parity", game.move_types)
    
    def test_get_game_type_not_found(self):
        """Test getting non-existent game type."""
        with self.assertRaises(ValueError) as context:
            self.loader.get_game_type("nonexistent_game")
        
        self.assertIn("not found", str(context.exception))
    
    def test_clear_cache(self):
        """Test clearing cache."""
        # Load something to populate cache
        system1 = self.loader.load_system()
        
        # Clear cache
        self.loader.clear_cache()
        
        # Load again - should be different object
        system2 = self.loader.load_system()
        
        # Values should be same, but different objects
        self.assertEqual(system1.protocol_version, system2.protocol_version)
    
    def test_reload_system(self):
        """Test force reloading system config."""
        system1 = self.loader.load_system()
        system2 = self.loader.reload_system()
        
        # Should be different objects after reload
        self.assertIsNot(system1, system2)
        self.assertEqual(system1.protocol_version, system2.protocol_version)


class TestConfigLoaderNetworkConfig(unittest.TestCase):
    """Tests for network configuration values."""
    
    def test_port_ranges(self):
        """Test that port ranges are valid."""
        loader = ConfigLoader()
        system = loader.load_system()
        
        # League manager port
        self.assertGreater(system.network.default_league_manager_port, 0)
        self.assertLess(system.network.default_league_manager_port, 65536)
        
        # Referee port range
        ref_range = system.network.default_referee_port_range
        self.assertEqual(len(ref_range), 2)
        self.assertLess(ref_range[0], ref_range[1])
        
        # Player port range
        player_range = system.network.default_player_port_range
        self.assertEqual(len(player_range), 2)
        self.assertLess(player_range[0], player_range[1])


if __name__ == "__main__":
    unittest.main()

