"""
Data Repositories - Runtime data management using the Repository Pattern.

Based on Chapter 10 of the League Protocol specification.
Implements repositories for standings, matches, and player history.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default data root
DATA_ROOT = Path(__file__).parent.parent / "data"


class StandingsRepository:
    """
    Repository for league standings data.
    
    Manages the standings.json file for a specific league.
    Located at: SHARED/data/leagues/<league_id>/standings.json
    """
    
    def __init__(self, league_id: str, data_root: Path = DATA_ROOT):
        """
        Initialize the StandingsRepository.
        
        Args:
            league_id: The league identifier.
            data_root: Root directory for data files.
        """
        self.league_id = league_id
        self.path = data_root / "leagues" / league_id / "standings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """
        Load standings from JSON file.
        
        Returns:
            Dict containing standings data.
        """
        if not self.path.exists():
            return {
                "schema_version": "1.0.0",
                "league_id": self.league_id,
                "version": 0,
                "rounds_completed": 0,
                "standings": [],
                "last_updated": None,
            }
        return json.loads(self.path.read_text(encoding="utf-8"))
    
    def save(self, standings: Dict[str, Any]) -> None:
        """
        Save standings to JSON file.
        
        Args:
            standings: The standings data to save.
        """
        standings["last_updated"] = datetime.utcnow().isoformat() + "Z"
        standings["version"] = standings.get("version", 0) + 1
        self.path.write_text(
            json.dumps(standings, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def get_standings(self) -> List[Dict[str, Any]]:
        """Get the current standings list."""
        data = self.load()
        return data.get("standings", [])
    
    def get_player_standing(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific player's standing.
        
        Args:
            player_id: The player identifier.
        
        Returns:
            The player's standing data, or None if not found.
        """
        standings = self.get_standings()
        for standing in standings:
            if standing.get("player_id") == player_id:
                return standing
        return None
    
    def update_player(
        self,
        player_id: str,
        display_name: str,
        result: str,
        points: int
    ) -> None:
        """
        Update a player's standings after a match.
        
        Args:
            player_id: The player identifier.
            display_name: The player's display name.
            result: Match result ("WIN", "DRAW", "LOSS", "TECHNICAL_LOSS").
            points: Points earned from the match.
        """
        data = self.load()
        standings = data.get("standings", [])
        
        # Find or create player entry
        player_entry = None
        for entry in standings:
            if entry["player_id"] == player_id:
                player_entry = entry
                break
        
        if player_entry is None:
            player_entry = {
                "player_id": player_id,
                "display_name": display_name,
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "points": 0,
                "rank": len(standings) + 1,
            }
            standings.append(player_entry)
        
        # Update stats
        player_entry["played"] += 1
        player_entry["points"] += points
        
        if result == "WIN":
            player_entry["wins"] += 1
        elif result == "DRAW":
            player_entry["draws"] += 1
        elif result in ("LOSS", "TECHNICAL_LOSS"):
            player_entry["losses"] += 1
        
        # Re-sort and update ranks
        standings.sort(key=lambda x: (-x["points"], -x["wins"], -x["draws"]))
        for i, entry in enumerate(standings):
            entry["rank"] = i + 1
        
        data["standings"] = standings
        self.save(data)
    
    def increment_rounds_completed(self) -> None:
        """Increment the rounds completed counter."""
        data = self.load()
        data["rounds_completed"] = data.get("rounds_completed", 0) + 1
        self.save(data)


class MatchRepository:
    """
    Repository for individual match data.
    
    Manages match JSON files for a specific league.
    Located at: SHARED/data/matches/<league_id>/<match_id>.json
    """
    
    def __init__(self, league_id: str, data_root: Path = DATA_ROOT):
        """
        Initialize the MatchRepository.
        
        Args:
            league_id: The league identifier.
            data_root: Root directory for data files.
        """
        self.league_id = league_id
        self.base_path = data_root / "matches" / league_id
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_match_path(self, match_id: str) -> Path:
        """Get the path for a specific match file."""
        return self.base_path / f"{match_id}.json"
    
    def load(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Load match data from JSON file.
        
        Args:
            match_id: The match identifier.
        
        Returns:
            Match data dict, or None if not found.
        """
        path = self._get_match_path(match_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    
    def save(self, match_id: str, match_data: Dict[str, Any]) -> None:
        """
        Save match data to JSON file.
        
        Args:
            match_id: The match identifier.
            match_data: The match data to save.
        """
        path = self._get_match_path(match_id)
        match_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        path.write_text(
            json.dumps(match_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def create_match(
        self,
        match_id: str,
        round_id: int,
        game_type: str,
        player_a_id: str,
        player_b_id: str,
        referee_id: str
    ) -> Dict[str, Any]:
        """
        Create a new match record.
        
        Args:
            match_id: The match identifier.
            round_id: The round number.
            game_type: The type of game.
            player_a_id: Player A's identifier.
            player_b_id: Player B's identifier.
            referee_id: The referee's identifier.
        
        Returns:
            The created match data.
        """
        match_data = {
            "schema_version": "1.0.0",
            "match_id": match_id,
            "league_id": self.league_id,
            "round_id": round_id,
            "game_type": game_type,
            "players": {
                "player_a": player_a_id,
                "player_b": player_b_id,
            },
            "referee_id": referee_id,
            "lifecycle": {
                "state": "CREATED",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "started_at": None,
                "finished_at": None,
            },
            "transcript": [],
            "result": None,
        }
        self.save(match_id, match_data)
        return match_data
    
    def update_state(self, match_id: str, new_state: str) -> None:
        """
        Update the match state.
        
        Args:
            match_id: The match identifier.
            new_state: The new state (e.g., "WAITING_FOR_PLAYERS", "COLLECTING_CHOICES").
        """
        match_data = self.load(match_id)
        if match_data:
            match_data["lifecycle"]["state"] = new_state
            if new_state == "WAITING_FOR_PLAYERS":
                match_data["lifecycle"]["started_at"] = datetime.utcnow().isoformat() + "Z"
            elif new_state == "FINISHED":
                match_data["lifecycle"]["finished_at"] = datetime.utcnow().isoformat() + "Z"
            self.save(match_id, match_data)
    
    def add_transcript_entry(
        self,
        match_id: str,
        message_type: str,
        sender: str,
        recipient: str,
        content: Dict[str, Any]
    ) -> None:
        """
        Add an entry to the match transcript.
        
        Args:
            match_id: The match identifier.
            message_type: The type of message.
            sender: The sender identifier.
            recipient: The recipient identifier.
            content: The message content.
        """
        match_data = self.load(match_id)
        if match_data:
            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message_type": message_type,
                "sender": sender,
                "recipient": recipient,
                "content": content,
            }
            match_data["transcript"].append(entry)
            self.save(match_id, match_data)
    
    def set_result(
        self,
        match_id: str,
        status: str,
        winner: Optional[str],
        details: Dict[str, Any]
    ) -> None:
        """
        Set the match result.
        
        Args:
            match_id: The match identifier.
            status: Result status ("WIN", "DRAW", "TECHNICAL_LOSS").
            winner: The winner's player_id, or None for a draw.
            details: Additional result details.
        """
        match_data = self.load(match_id)
        if match_data:
            match_data["result"] = {
                "status": status,
                "winner": winner,
                "details": details,
                "recorded_at": datetime.utcnow().isoformat() + "Z",
            }
            match_data["lifecycle"]["state"] = "FINISHED"
            match_data["lifecycle"]["finished_at"] = datetime.utcnow().isoformat() + "Z"
            self.save(match_id, match_data)
    
    def list_matches(self) -> List[str]:
        """List all match IDs in this league."""
        return [p.stem for p in self.base_path.glob("*.json")]


class PlayerHistoryRepository:
    """
    Repository for player match history.
    
    Manages history.json files for individual players.
    Located at: SHARED/data/players/<player_id>/history.json
    """
    
    def __init__(self, player_id: str, data_root: Path = DATA_ROOT):
        """
        Initialize the PlayerHistoryRepository.
        
        Args:
            player_id: The player identifier.
            data_root: Root directory for data files.
        """
        self.player_id = player_id
        self.path = data_root / "players" / player_id / "history.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> Dict[str, Any]:
        """
        Load player history from JSON file.
        
        Returns:
            Dict containing player history data.
        """
        if not self.path.exists():
            return {
                "schema_version": "1.0.0",
                "player_id": self.player_id,
                "stats": {
                    "total_matches": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                },
                "matches": [],
                "last_updated": None,
            }
        return json.loads(self.path.read_text(encoding="utf-8"))
    
    def save(self, history: Dict[str, Any]) -> None:
        """
        Save player history to JSON file.
        
        Args:
            history: The history data to save.
        """
        history["last_updated"] = datetime.utcnow().isoformat() + "Z"
        self.path.write_text(
            json.dumps(history, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def add_match(
        self,
        match_id: str,
        league_id: str,
        opponent_id: str,
        result: str,
        my_choice: Optional[str] = None,
        opponent_choice: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a match in the player's history.
        
        Args:
            match_id: The match identifier.
            league_id: The league identifier.
            opponent_id: The opponent's player_id.
            result: Match result ("WIN", "DRAW", "LOSS", "TECHNICAL_LOSS").
            my_choice: The player's choice (game-specific).
            opponent_choice: The opponent's choice.
            details: Additional match details.
        """
        history = self.load()
        
        # Update stats
        history["stats"]["total_matches"] += 1
        if result == "WIN":
            history["stats"]["wins"] += 1
        elif result == "DRAW":
            history["stats"]["draws"] += 1
        elif result in ("LOSS", "TECHNICAL_LOSS"):
            history["stats"]["losses"] += 1
        
        # Add match record
        match_record = {
            "match_id": match_id,
            "league_id": league_id,
            "opponent_id": opponent_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if my_choice is not None:
            match_record["my_choice"] = my_choice
        if opponent_choice is not None:
            match_record["opponent_choice"] = opponent_choice
        if details:
            match_record["details"] = details
        
        history["matches"].append(match_record)
        self.save(history)
    
    def get_stats(self) -> Dict[str, int]:
        """Get the player's statistics."""
        history = self.load()
        return history.get("stats", {})
    
    def get_matches(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the player's match history.
        
        Args:
            limit: Maximum number of matches to return (most recent first).
        
        Returns:
            List of match records.
        """
        history = self.load()
        matches = history.get("matches", [])
        
        # Return most recent first
        matches = list(reversed(matches))
        
        if limit is not None:
            matches = matches[:limit]
        
        return matches
    
    def get_matches_against(self, opponent_id: str) -> List[Dict[str, Any]]:
        """
        Get all matches against a specific opponent.
        
        Args:
            opponent_id: The opponent's player_id.
        
        Returns:
            List of match records against this opponent.
        """
        history = self.load()
        return [
            match for match in history.get("matches", [])
            if match.get("opponent_id") == opponent_id
        ]
    
    def get_win_rate(self) -> float:
        """
        Calculate the player's win rate.
        
        Returns:
            Win rate as a float between 0 and 1, or 0 if no matches.
        """
        stats = self.get_stats()
        total = stats.get("total_matches", 0)
        if total == 0:
            return 0.0
        return stats.get("wins", 0) / total

