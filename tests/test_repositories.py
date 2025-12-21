"""
Unit tests for repositories.py
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add SHARED to path
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

import unittest
from league_sdk.repositories import (
    StandingsRepository,
    MatchRepository,
    PlayerHistoryRepository,
)


class TestStandingsRepository(unittest.TestCase):
    """Tests for StandingsRepository class."""
    
    def setUp(self):
        """Set up test fixtures with temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = StandingsRepository("test_league", data_root=self.temp_dir)
    
    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_load_empty(self):
        """Test loading from non-existent file."""
        data = self.repo.load()
        
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertEqual(data["league_id"], "test_league")
        self.assertEqual(data["standings"], [])
    
    def test_save_and_load(self):
        """Test saving and loading standings."""
        standings = {
            "schema_version": "1.0.0",
            "league_id": "test_league",
            "version": 1,
            "standings": [
                {"player_id": "P01", "points": 6, "rank": 1}
            ]
        }
        
        self.repo.save(standings)
        loaded = self.repo.load()
        
        self.assertEqual(len(loaded["standings"]), 1)
        self.assertEqual(loaded["standings"][0]["player_id"], "P01")
        self.assertIsNotNone(loaded["last_updated"])
    
    def test_update_player_win(self):
        """Test updating player after a win."""
        self.repo.update_player("P01", "Agent Alpha", "WIN", 3)
        
        standings = self.repo.get_standings()
        self.assertEqual(len(standings), 1)
        self.assertEqual(standings[0]["player_id"], "P01")
        self.assertEqual(standings[0]["wins"], 1)
        self.assertEqual(standings[0]["points"], 3)
    
    def test_update_player_draw(self):
        """Test updating player after a draw."""
        self.repo.update_player("P01", "Agent Alpha", "DRAW", 1)
        
        standings = self.repo.get_standings()
        self.assertEqual(standings[0]["draws"], 1)
        self.assertEqual(standings[0]["points"], 1)
    
    def test_update_player_loss(self):
        """Test updating player after a loss."""
        self.repo.update_player("P01", "Agent Alpha", "LOSS", 0)
        
        standings = self.repo.get_standings()
        self.assertEqual(standings[0]["losses"], 1)
        self.assertEqual(standings[0]["points"], 0)
    
    def test_multiple_updates(self):
        """Test multiple updates for same player."""
        self.repo.update_player("P01", "Agent Alpha", "WIN", 3)
        self.repo.update_player("P01", "Agent Alpha", "WIN", 3)
        self.repo.update_player("P01", "Agent Alpha", "DRAW", 1)
        
        standings = self.repo.get_standings()
        self.assertEqual(standings[0]["played"], 3)
        self.assertEqual(standings[0]["wins"], 2)
        self.assertEqual(standings[0]["draws"], 1)
        self.assertEqual(standings[0]["points"], 7)  # 3+3+1
    
    def test_ranking_order(self):
        """Test that standings are sorted by points."""
        self.repo.update_player("P01", "Agent Alpha", "WIN", 3)
        self.repo.update_player("P02", "Agent Beta", "WIN", 3)
        self.repo.update_player("P02", "Agent Beta", "WIN", 3)
        self.repo.update_player("P03", "Agent Gamma", "LOSS", 0)
        
        standings = self.repo.get_standings()
        
        # P02 should be first (6 points)
        self.assertEqual(standings[0]["player_id"], "P02")
        self.assertEqual(standings[0]["rank"], 1)
        
        # P01 should be second (3 points)
        self.assertEqual(standings[1]["player_id"], "P01")
        self.assertEqual(standings[1]["rank"], 2)
    
    def test_get_player_standing(self):
        """Test getting specific player's standing."""
        self.repo.update_player("P01", "Agent Alpha", "WIN", 3)
        self.repo.update_player("P02", "Agent Beta", "LOSS", 0)
        
        standing = self.repo.get_player_standing("P01")
        self.assertIsNotNone(standing)
        self.assertEqual(standing["points"], 3)
        
        # Non-existent player
        standing = self.repo.get_player_standing("P99")
        self.assertIsNone(standing)
    
    def test_increment_rounds_completed(self):
        """Test incrementing rounds completed counter."""
        self.repo.increment_rounds_completed()
        data = self.repo.load()
        self.assertEqual(data["rounds_completed"], 1)
        
        self.repo.increment_rounds_completed()
        data = self.repo.load()
        self.assertEqual(data["rounds_completed"], 2)


class TestMatchRepository(unittest.TestCase):
    """Tests for MatchRepository class."""
    
    def setUp(self):
        """Set up test fixtures with temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = MatchRepository("test_league", data_root=self.temp_dir)
    
    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_match(self):
        """Test creating a new match."""
        match = self.repo.create_match(
            match_id="R1M1",
            round_id=1,
            game_type="even_odd",
            player_a_id="P01",
            player_b_id="P02",
            referee_id="REF01"
        )
        
        self.assertEqual(match["match_id"], "R1M1")
        self.assertEqual(match["round_id"], 1)
        self.assertEqual(match["players"]["player_a"], "P01")
        self.assertEqual(match["lifecycle"]["state"], "CREATED")
    
    def test_load_match(self):
        """Test loading a created match."""
        self.repo.create_match(
            match_id="R1M1",
            round_id=1,
            game_type="even_odd",
            player_a_id="P01",
            player_b_id="P02",
            referee_id="REF01"
        )
        
        match = self.repo.load("R1M1")
        self.assertIsNotNone(match)
        self.assertEqual(match["match_id"], "R1M1")
    
    def test_load_nonexistent_match(self):
        """Test loading non-existent match."""
        match = self.repo.load("NONEXISTENT")
        self.assertIsNone(match)
    
    def test_update_state(self):
        """Test updating match state."""
        self.repo.create_match(
            match_id="R1M1",
            round_id=1,
            game_type="even_odd",
            player_a_id="P01",
            player_b_id="P02",
            referee_id="REF01"
        )
        
        self.repo.update_state("R1M1", "COLLECTING_CHOICES")
        match = self.repo.load("R1M1")
        self.assertEqual(match["lifecycle"]["state"], "COLLECTING_CHOICES")
    
    def test_add_transcript_entry(self):
        """Test adding transcript entry."""
        self.repo.create_match(
            match_id="R1M1",
            round_id=1,
            game_type="even_odd",
            player_a_id="P01",
            player_b_id="P02",
            referee_id="REF01"
        )
        
        self.repo.add_transcript_entry(
            match_id="R1M1",
            message_type="GAME_INVITATION",
            sender="referee:REF01",
            recipient="player:P01",
            content={"match_id": "R1M1"}
        )
        
        match = self.repo.load("R1M1")
        self.assertEqual(len(match["transcript"]), 1)
        self.assertEqual(match["transcript"][0]["message_type"], "GAME_INVITATION")
    
    def test_set_result(self):
        """Test setting match result."""
        self.repo.create_match(
            match_id="R1M1",
            round_id=1,
            game_type="even_odd",
            player_a_id="P01",
            player_b_id="P02",
            referee_id="REF01"
        )
        
        self.repo.set_result(
            match_id="R1M1",
            status="WIN",
            winner="P01",
            details={"drawn_number": 8, "number_parity": "even"}
        )
        
        match = self.repo.load("R1M1")
        self.assertEqual(match["result"]["status"], "WIN")
        self.assertEqual(match["result"]["winner"], "P01")
        self.assertEqual(match["lifecycle"]["state"], "FINISHED")
    
    def test_list_matches(self):
        """Test listing all matches."""
        self.repo.create_match("R1M1", 1, "even_odd", "P01", "P02", "REF01")
        self.repo.create_match("R1M2", 1, "even_odd", "P03", "P04", "REF01")
        
        matches = self.repo.list_matches()
        self.assertEqual(len(matches), 2)
        self.assertIn("R1M1", matches)
        self.assertIn("R1M2", matches)


class TestPlayerHistoryRepository(unittest.TestCase):
    """Tests for PlayerHistoryRepository class."""
    
    def setUp(self):
        """Set up test fixtures with temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = PlayerHistoryRepository("P01", data_root=self.temp_dir)
    
    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_load_empty(self):
        """Test loading from non-existent file."""
        data = self.repo.load()
        
        self.assertEqual(data["player_id"], "P01")
        self.assertEqual(data["stats"]["total_matches"], 0)
        self.assertEqual(data["matches"], [])
    
    def test_add_match_win(self):
        """Test adding a win."""
        self.repo.add_match(
            match_id="R1M1",
            league_id="test_league",
            opponent_id="P02",
            result="WIN",
            my_choice="even",
            opponent_choice="odd"
        )
        
        stats = self.repo.get_stats()
        self.assertEqual(stats["total_matches"], 1)
        self.assertEqual(stats["wins"], 1)
        self.assertEqual(stats["losses"], 0)
    
    def test_add_match_loss(self):
        """Test adding a loss."""
        self.repo.add_match(
            match_id="R1M1",
            league_id="test_league",
            opponent_id="P02",
            result="LOSS"
        )
        
        stats = self.repo.get_stats()
        self.assertEqual(stats["losses"], 1)
    
    def test_add_match_draw(self):
        """Test adding a draw."""
        self.repo.add_match(
            match_id="R1M1",
            league_id="test_league",
            opponent_id="P02",
            result="DRAW"
        )
        
        stats = self.repo.get_stats()
        self.assertEqual(stats["draws"], 1)
    
    def test_get_matches_limit(self):
        """Test getting matches with limit."""
        for i in range(5):
            self.repo.add_match(
                match_id=f"R1M{i}",
                league_id="test_league",
                opponent_id="P02",
                result="WIN"
            )
        
        matches = self.repo.get_matches(limit=3)
        self.assertEqual(len(matches), 3)
    
    def test_get_matches_against(self):
        """Test getting matches against specific opponent."""
        self.repo.add_match("R1M1", "league", "P02", "WIN")
        self.repo.add_match("R1M2", "league", "P03", "LOSS")
        self.repo.add_match("R2M1", "league", "P02", "DRAW")
        
        matches = self.repo.get_matches_against("P02")
        self.assertEqual(len(matches), 2)
    
    def test_get_win_rate(self):
        """Test calculating win rate."""
        self.repo.add_match("R1M1", "league", "P02", "WIN")
        self.repo.add_match("R1M2", "league", "P03", "WIN")
        self.repo.add_match("R2M1", "league", "P02", "LOSS")
        self.repo.add_match("R2M2", "league", "P04", "WIN")
        
        win_rate = self.repo.get_win_rate()
        self.assertEqual(win_rate, 0.75)  # 3 wins out of 4
    
    def test_get_win_rate_no_matches(self):
        """Test win rate with no matches."""
        win_rate = self.repo.get_win_rate()
        self.assertEqual(win_rate, 0.0)


if __name__ == "__main__":
    unittest.main()

