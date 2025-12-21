"""
Unit tests for scheduler.py (Round-Robin scheduling)
"""

import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "league_manager"))

import unittest
from scheduler import RoundRobinScheduler


class TestRoundRobinScheduler(unittest.TestCase):
    """Tests for RoundRobinScheduler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.scheduler = RoundRobinScheduler()
    
    def test_create_schedule_4_players(self):
        """Test creating schedule for 4 players."""
        players = ["P01", "P02", "P03", "P04"]
        schedule = self.scheduler.create_schedule(players)
        
        # 4 players = 3 rounds
        self.assertEqual(len(schedule), 3)
        
        # Each round has 2 matches
        for round_matches in schedule:
            self.assertEqual(len(round_matches), 2)
    
    def test_create_schedule_2_players(self):
        """Test creating schedule for 2 players."""
        players = ["P01", "P02"]
        schedule = self.scheduler.create_schedule(players)
        
        # 2 players = 1 round
        self.assertEqual(len(schedule), 1)
        self.assertEqual(len(schedule[0]), 1)
        self.assertEqual(schedule[0][0], ("P01", "P02"))
    
    def test_create_schedule_3_players(self):
        """Test creating schedule for 3 players (odd)."""
        players = ["P01", "P02", "P03"]
        schedule = self.scheduler.create_schedule(players)
        
        # 3 players = 3 rounds (with BYE)
        self.assertEqual(len(schedule), 3)
        
        # Total matches should be 3 (n(n-1)/2 = 3*2/2)
        total_matches = sum(len(r) for r in schedule)
        self.assertEqual(total_matches, 3)
    
    def test_create_schedule_empty(self):
        """Test creating schedule with less than 2 players."""
        self.assertEqual(self.scheduler.create_schedule([]), [])
        self.assertEqual(self.scheduler.create_schedule(["P01"]), [])
    
    def test_each_player_plays_all_others(self):
        """Test that each player plays against all others."""
        players = ["P01", "P02", "P03", "P04"]
        schedule = self.scheduler.create_schedule(players)
        
        # Collect all matches per player
        matches_per_player = {p: [] for p in players}
        
        for round_matches in schedule:
            for player_a, player_b in round_matches:
                matches_per_player[player_a].append(player_b)
                matches_per_player[player_b].append(player_a)
        
        # Each player should have played 3 matches (n-1)
        for player, opponents in matches_per_player.items():
            self.assertEqual(len(opponents), 3,
                           f"{player} played {len(opponents)} matches instead of 3")
    
    def test_no_duplicate_matches(self):
        """Test that no match is played twice."""
        players = ["P01", "P02", "P03", "P04"]
        schedule = self.scheduler.create_schedule(players)
        
        all_matches = []
        for round_matches in schedule:
            for match in round_matches:
                # Normalize match order for comparison
                normalized = tuple(sorted(match))
                self.assertNotIn(normalized, all_matches,
                               f"Duplicate match: {match}")
                all_matches.append(normalized)
    
    def test_no_self_play(self):
        """Test that no player plays against themselves."""
        players = ["P01", "P02", "P03", "P04"]
        schedule = self.scheduler.create_schedule(players)
        
        for round_matches in schedule:
            for player_a, player_b in round_matches:
                self.assertNotEqual(player_a, player_b,
                                   f"Self-play detected: {player_a}")
    
    def test_get_total_matches(self):
        """Test calculating total matches."""
        self.assertEqual(self.scheduler.get_total_matches(2), 1)
        self.assertEqual(self.scheduler.get_total_matches(3), 3)
        self.assertEqual(self.scheduler.get_total_matches(4), 6)
        self.assertEqual(self.scheduler.get_total_matches(5), 10)
        self.assertEqual(self.scheduler.get_total_matches(10), 45)
    
    def test_get_num_rounds(self):
        """Test calculating number of rounds."""
        self.assertEqual(self.scheduler.get_num_rounds(2), 1)
        self.assertEqual(self.scheduler.get_num_rounds(4), 3)
        self.assertEqual(self.scheduler.get_num_rounds(6), 5)
        
        # Odd numbers get +1 for BYE
        self.assertEqual(self.scheduler.get_num_rounds(3), 3)
        self.assertEqual(self.scheduler.get_num_rounds(5), 5)
    
    def test_get_matches_per_round(self):
        """Test calculating matches per round."""
        self.assertEqual(self.scheduler.get_matches_per_round(4), 2)
        self.assertEqual(self.scheduler.get_matches_per_round(6), 3)
        self.assertEqual(self.scheduler.get_matches_per_round(10), 5)
    
    def test_validate_schedule_valid(self):
        """Test validating a valid schedule."""
        players = ["P01", "P02", "P03", "P04"]
        schedule = self.scheduler.create_schedule(players)
        
        self.assertTrue(self.scheduler.validate_schedule(schedule, players))
    
    def test_validate_schedule_invalid_duplicate(self):
        """Test validating schedule with duplicate match."""
        players = ["P01", "P02", "P03", "P04"]
        
        # Create invalid schedule with duplicate
        schedule = [
            [("P01", "P02"), ("P03", "P04")],
            [("P01", "P02"), ("P03", "P04")],  # Duplicate!
        ]
        
        self.assertFalse(self.scheduler.validate_schedule(schedule, players))
    
    def test_validate_schedule_invalid_self_play(self):
        """Test validating schedule with self-play."""
        players = ["P01", "P02"]
        
        schedule = [
            [("P01", "P01")],  # Self-play!
        ]
        
        self.assertFalse(self.scheduler.validate_schedule(schedule, players))
    
    def test_print_schedule(self):
        """Test printing schedule."""
        players = ["P01", "P02", "P03", "P04"]
        schedule = self.scheduler.create_schedule(players)
        
        output = self.scheduler.print_schedule(schedule)
        
        self.assertIn("Round 1", output)
        self.assertIn("Round 2", output)
        self.assertIn("Round 3", output)
        self.assertIn("Match", output)
        self.assertIn("vs", output)


class TestRoundRobinSchedulerLargeScale(unittest.TestCase):
    """Large-scale tests for Round-Robin scheduler."""
    
    def test_schedule_10_players(self):
        """Test scheduling 10 players."""
        scheduler = RoundRobinScheduler()
        players = [f"P{i:02d}" for i in range(1, 11)]
        
        schedule = scheduler.create_schedule(players)
        
        # 10 players = 9 rounds
        self.assertEqual(len(schedule), 9)
        
        # Each round has 5 matches
        for round_matches in schedule:
            self.assertEqual(len(round_matches), 5)
        
        # Total matches = 45
        total = sum(len(r) for r in schedule)
        self.assertEqual(total, 45)
        
        # Validate
        self.assertTrue(scheduler.validate_schedule(schedule, players))
    
    def test_schedule_7_players_odd(self):
        """Test scheduling 7 players (odd number)."""
        scheduler = RoundRobinScheduler()
        players = [f"P{i:02d}" for i in range(1, 8)]
        
        schedule = scheduler.create_schedule(players)
        
        # 7 players = 7 rounds (with BYE)
        self.assertEqual(len(schedule), 7)
        
        # Total matches = 21 (7*6/2)
        total = sum(len(r) for r in schedule)
        self.assertEqual(total, 21)
        
        # Validate
        self.assertTrue(scheduler.validate_schedule(schedule, players))


if __name__ == "__main__":
    unittest.main()

