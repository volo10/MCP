"""
Round-Robin Scheduler - Match scheduling algorithm.

Based on Chapter 3.5 and 8.5 of the League Protocol specification.

For n players, creates n-1 rounds where each player plays against
every other player exactly once.

Total matches = n(n-1)/2
"""

from typing import List, Tuple


class RoundRobinScheduler:
    """
    Round-Robin tournament scheduler.
    
    Creates a schedule where each player plays against every other
    player exactly once. The algorithm handles both even and odd
    numbers of players.
    
    For 4 players: 3 rounds, 6 total matches
    - Round 1: P1 vs P2, P3 vs P4
    - Round 2: P1 vs P3, P2 vs P4
    - Round 3: P1 vs P4, P2 vs P3
    """
    
    def create_schedule(self, player_ids: List[str]) -> List[List[Tuple[str, str]]]:
        """
        Create a Round-Robin schedule for all players.
        
        Args:
            player_ids: List of player identifiers.
        
        Returns:
            List of rounds, where each round is a list of match tuples
            (player_A, player_B).
        
        Example:
            scheduler = RoundRobinScheduler()
            schedule = scheduler.create_schedule(["P01", "P02", "P03", "P04"])
            # Returns:
            # [
            #     [("P01", "P04"), ("P02", "P03")],  # Round 1
            #     [("P01", "P03"), ("P04", "P02")],  # Round 2
            #     [("P01", "P02"), ("P03", "P04")]   # Round 3
            # ]
        """
        n = len(player_ids)
        
        if n < 2:
            return []
        
        # Make a copy to avoid modifying the original
        players = list(player_ids)
        
        # If odd number of players, add a "BYE" placeholder
        if n % 2 == 1:
            players.append("BYE")
            n += 1
        
        schedule = []
        num_rounds = n - 1
        
        # Use the circle method (rotation algorithm)
        # Fix one player (first) and rotate the rest
        for round_num in range(num_rounds):
            round_matches = []
            
            for i in range(n // 2):
                player_a = players[i]
                player_b = players[n - 1 - i]
                
                # Skip matches with "BYE"
                if player_a != "BYE" and player_b != "BYE":
                    round_matches.append((player_a, player_b))
            
            schedule.append(round_matches)
            
            # Rotate: keep first player fixed, rotate the rest
            # [1, 2, 3, 4] -> [1, 4, 2, 3]
            players = [players[0]] + [players[-1]] + players[1:-1]
        
        return schedule
    
    def get_total_matches(self, num_players: int) -> int:
        """
        Calculate total number of matches in a Round-Robin tournament.
        
        Formula: n(n-1)/2
        
        Args:
            num_players: Number of players.
        
        Returns:
            Total number of matches.
        """
        return num_players * (num_players - 1) // 2
    
    def get_num_rounds(self, num_players: int) -> int:
        """
        Calculate number of rounds in a Round-Robin tournament.
        
        Args:
            num_players: Number of players.
        
        Returns:
            Number of rounds.
        """
        if num_players % 2 == 0:
            return num_players - 1
        else:
            return num_players  # With BYE added
    
    def get_matches_per_round(self, num_players: int) -> int:
        """
        Calculate matches per round.
        
        Args:
            num_players: Number of players.
        
        Returns:
            Matches per round (some rounds may have fewer if odd players).
        """
        return num_players // 2
    
    def validate_schedule(self, schedule: List[List[Tuple[str, str]]], 
                         player_ids: List[str]) -> bool:
        """
        Validate that a schedule is a valid Round-Robin tournament.
        
        Checks:
        - Each player plays exactly n-1 matches
        - Each pair plays exactly once
        - No player plays themselves
        
        Args:
            schedule: The schedule to validate.
            player_ids: List of player identifiers.
        
        Returns:
            True if valid, False otherwise.
        """
        expected_matches = self.get_total_matches(len(player_ids))
        
        # Track all matches
        all_matches = []
        player_match_counts = {pid: 0 for pid in player_ids}
        
        for round_matches in schedule:
            for player_a, player_b in round_matches:
                # Check no self-play
                if player_a == player_b:
                    return False
                
                # Normalize match order for duplicate checking
                match = tuple(sorted([player_a, player_b]))
                
                # Check no duplicate matches
                if match in all_matches:
                    return False
                
                all_matches.append(match)
                
                # Count matches per player
                if player_a in player_match_counts:
                    player_match_counts[player_a] += 1
                if player_b in player_match_counts:
                    player_match_counts[player_b] += 1
        
        # Check total matches
        if len(all_matches) != expected_matches:
            return False
        
        # Check each player plays n-1 matches
        expected_per_player = len(player_ids) - 1
        for pid, count in player_match_counts.items():
            if count != expected_per_player:
                return False
        
        return True
    
    def print_schedule(self, schedule: List[List[Tuple[str, str]]]) -> str:
        """
        Format schedule as a readable string.
        
        Args:
            schedule: The schedule to format.
        
        Returns:
            Formatted string representation.
        """
        lines = []
        for round_num, round_matches in enumerate(schedule, 1):
            lines.append(f"Round {round_num}:")
            for match_num, (player_a, player_b) in enumerate(round_matches, 1):
                lines.append(f"  Match {match_num}: {player_a} vs {player_b}")
        return "\n".join(lines)


# Example usage and testing
if __name__ == "__main__":
    scheduler = RoundRobinScheduler()
    
    # Test with 4 players (as per specification)
    players = ["P01", "P02", "P03", "P04"]
    schedule = scheduler.create_schedule(players)
    
    print("Round-Robin Schedule for 4 Players")
    print("=" * 40)
    print(scheduler.print_schedule(schedule))
    print()
    print(f"Total matches: {scheduler.get_total_matches(len(players))}")
    print(f"Total rounds: {scheduler.get_num_rounds(len(players))}")
    print(f"Schedule valid: {scheduler.validate_schedule(schedule, players)}")

