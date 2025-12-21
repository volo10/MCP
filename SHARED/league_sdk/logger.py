"""
JSON Logger - Structured logging in JSONL format.

Based on Chapter 10 of the League Protocol specification.
Writes structured logs in JSON Lines format for easy parsing and analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Default log root
LOG_ROOT = Path(__file__).parent.parent / "logs"


class JsonLogger:
    """
    Structured logger that writes logs in JSONL (JSON Lines) format.
    
    Each log entry is a JSON object on its own line, enabling:
    - Efficient append-only writes
    - Easy parsing with standard tools
    - Real-time log streaming
    
    Log files are organized by:
    - League logs: logs/league/<league_id>/
    - Agent logs: logs/agents/<agent_id>.log.jsonl
    - System logs: logs/system/
    """
    
    def __init__(
        self,
        component: str,
        league_id: Optional[str] = None,
        log_root: Path = LOG_ROOT
    ):
        """
        Initialize the JsonLogger.
        
        Args:
            component: The component name (e.g., "league_manager", "referee:REF01").
            league_id: Optional league ID for league-specific logs.
            log_root: Root directory for log files.
        """
        self.component = component
        self.league_id = league_id
        self.log_root = Path(log_root)
        
        # Determine log directory and file
        if league_id:
            subdir = self.log_root / "league" / league_id
        elif component.startswith("referee:") or component.startswith("player:"):
            subdir = self.log_root / "agents"
        else:
            subdir = self.log_root / "system"
        
        subdir.mkdir(parents=True, exist_ok=True)
        
        # Create log file name
        safe_component = component.replace(":", "_")
        self.log_file = subdir / f"{safe_component}.log.jsonl"
    
    def log(
        self,
        event_type: str,
        level: str = "INFO",
        **details: Any
    ) -> None:
        """
        Write a log entry.
        
        Format follows Chapter 9.5.1 of the League Protocol specification:
        {
            "timestamp": "2025-01-15T10:15:00Z",
            "component": "league_manager",
            "event_type": "ROUND_ANNOUNCEMENT_SENT",
            "level": "INFO",
            "details": { ... }
        }
        
        Args:
            event_type: The type of event being logged.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            **details: Additional key-value pairs to include in the log.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "component": self.component,
            "event_type": event_type,
            "level": level,
        }
        
        # Add league_id if available
        if self.league_id:
            entry["league_id"] = self.league_id
        
        # Add additional details in a 'details' object per Ch. 9.5.1
        if details:
            entry["details"] = details
        
        # Write to log file
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # =========================================================================
    # Convenience Methods for Log Levels
    # =========================================================================
    
    def debug(self, event_type: str, **details: Any) -> None:
        """Log a DEBUG level message."""
        self.log(event_type, level="DEBUG", **details)
    
    def info(self, event_type: str, **details: Any) -> None:
        """Log an INFO level message."""
        self.log(event_type, level="INFO", **details)
    
    def warning(self, event_type: str, **details: Any) -> None:
        """Log a WARNING level message."""
        self.log(event_type, level="WARNING", **details)
    
    def error(self, event_type: str, **details: Any) -> None:
        """Log an ERROR level message."""
        self.log(event_type, level="ERROR", **details)
    
    # =========================================================================
    # Convenience Methods for Common Events
    # =========================================================================
    
    def log_message_sent(
        self,
        message_type: str,
        recipient: str,
        **details: Any
    ) -> None:
        """
        Log a message being sent.
        
        Args:
            message_type: The type of message (e.g., "GAME_INVITATION").
            recipient: The recipient identifier.
            **details: Additional message details.
        """
        self.debug(
            "MESSAGE_SENT",
            message_type=message_type,
            recipient=recipient,
            **details
        )
    
    def log_message_received(
        self,
        message_type: str,
        sender: str,
        **details: Any
    ) -> None:
        """
        Log a message being received.
        
        Args:
            message_type: The type of message received.
            sender: The sender identifier.
            **details: Additional message details.
        """
        self.debug(
            "MESSAGE_RECEIVED",
            message_type=message_type,
            sender=sender,
            **details
        )
    
    def log_state_change(
        self,
        from_state: str,
        to_state: str,
        **details: Any
    ) -> None:
        """
        Log a state transition.
        
        Args:
            from_state: The previous state.
            to_state: The new state.
            **details: Additional context.
        """
        self.info(
            "STATE_CHANGE",
            from_state=from_state,
            to_state=to_state,
            **details
        )
    
    def log_game_error(
        self,
        error_code: str,
        error_description: str,
        match_id: Optional[str] = None,
        player_id: Optional[str] = None,
        **details: Any
    ) -> None:
        """
        Log a game error.
        
        Args:
            error_code: The error code (e.g., "E001").
            error_description: Human-readable error description.
            match_id: The match ID if applicable.
            player_id: The player ID if applicable.
            **details: Additional error context.
        """
        self.error(
            "GAME_ERROR",
            error_code=error_code,
            error_description=error_description,
            match_id=match_id,
            player_id=player_id,
            **details
        )
    
    def log_match_result(
        self,
        match_id: str,
        status: str,
        winner: Optional[str] = None,
        **details: Any
    ) -> None:
        """
        Log a match result.
        
        Args:
            match_id: The match identifier.
            status: Result status ("WIN", "DRAW", "TECHNICAL_LOSS").
            winner: The winner's player_id if applicable.
            **details: Additional result details.
        """
        self.info(
            "MATCH_RESULT",
            match_id=match_id,
            status=status,
            winner=winner,
            **details
        )
    
    def log_round_event(
        self,
        event_type: str,
        round_id: int,
        **details: Any
    ) -> None:
        """
        Log a round-related event.
        
        Args:
            event_type: The event type (e.g., "ROUND_STARTED", "ROUND_COMPLETED").
            round_id: The round number.
            **details: Additional event details.
        """
        self.info(
            event_type,
            round_id=round_id,
            **details
        )
    
    def log_registration(
        self,
        agent_type: str,
        agent_id: str,
        status: str,
        **details: Any
    ) -> None:
        """
        Log an agent registration event.
        
        Args:
            agent_type: Type of agent ("player", "referee").
            agent_id: The agent's identifier.
            status: Registration status ("ACCEPTED", "REJECTED").
            **details: Additional registration details.
        """
        level = "INFO" if status == "ACCEPTED" else "WARNING"
        self.log(
            "AGENT_REGISTRATION",
            level=level,
            agent_type=agent_type,
            agent_id=agent_id,
            status=status,
            **details
        )
    
    # =========================================================================
    # Log Reading (for debugging/analysis)
    # =========================================================================
    
    def read_logs(self, limit: Optional[int] = None) -> list[dict]:
        """
        Read log entries from the log file.
        
        Args:
            limit: Maximum number of entries to return (most recent first).
        
        Returns:
            List of log entry dictionaries.
        """
        if not self.log_file.exists():
            return []
        
        entries = []
        with self.log_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        # Return most recent first
        entries = list(reversed(entries))
        
        if limit is not None:
            entries = entries[:limit]
        
        return entries
    
    def read_errors(self, limit: Optional[int] = None) -> list[dict]:
        """
        Read only ERROR level entries.
        
        Args:
            limit: Maximum number of entries to return.
        
        Returns:
            List of error log entries.
        """
        all_logs = self.read_logs()
        errors = [entry for entry in all_logs if entry.get("level") == "ERROR"]
        
        if limit is not None:
            errors = errors[:limit]
        
        return errors

