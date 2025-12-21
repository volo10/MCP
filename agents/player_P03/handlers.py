"""
Player Handlers - Message handlers for the player agent.

Implements handlers for:
- GAME_INVITATION: Accept/reject game invitations
- CHOOSE_PARITY_CALL: Make parity choice
- GAME_OVER: Process match results
- ROUND_ANNOUNCEMENT: Track round information
- LEAGUE_STANDINGS_UPDATE: Track standings

Based on Chapters 3 and 4 of the League Protocol specification.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from main import PlayerState


class PlayerHandlers:
    """Handlers for player operations."""
    
    def __init__(self, state: "PlayerState"):
        self.state = state
    
    def _create_envelope(self, message_type: str, **extra_fields) -> dict:
        """Create a protocol envelope."""
        envelope = {
            "protocol": "league.v2",
            "message_type": message_type,
            "sender": f"player:{self.state.player_id}" if self.state.player_id else "player:UNREGISTERED",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self.state.auth_token:
            envelope["auth_token"] = self.state.auth_token
        
        envelope.update(extra_fields)
        return envelope
    
    # =========================================================================
    # Game Invitation Handler
    # =========================================================================
    
    async def handle_game_invitation(self, params: dict) -> dict:
        """
        Handle GAME_INVITATION from referee.
        
        Returns GAME_JOIN_ACK to confirm participation.
        
        Args:
            params: Invitation parameters including match_id, opponent_id, etc.
        
        Returns:
            GAME_JOIN_ACK response.
        """
        match_id = params.get("match_id")
        round_id = params.get("round_id")
        game_type = params.get("game_type")
        opponent_id = params.get("opponent_id")
        role = params.get("role_in_match")
        conversation_id = params.get("conversation_id")
        
        self.state.logger.info("GAME_INVITATION_RECEIVED",
                               match_id=match_id,
                               opponent_id=opponent_id,
                               role=role)
        
        # Store current match info
        self.state.current_match = {
            "match_id": match_id,
            "round_id": round_id,
            "game_type": game_type,
            "opponent_id": opponent_id,
            "role": role,
            "conversation_id": conversation_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "my_choice": None,
            "result": None
        }
        
        # Always accept (auto_accept_invitations)
        response = self._create_envelope(
            "GAME_JOIN_ACK",
            match_id=match_id,
            player_id=self.state.player_id,
            arrival_timestamp=datetime.utcnow().isoformat() + "Z",
            accept=True,
            accepted=True  # Include both for compatibility
        )
        
        self.state.logger.debug("GAME_JOIN_ACK_SENT", match_id=match_id)
        
        return response
    
    # =========================================================================
    # Choose Parity Handler
    # =========================================================================
    
    async def handle_choose_parity(self, params: dict) -> dict:
        """
        Handle CHOOSE_PARITY_CALL from referee.
        
        Uses the configured strategy to make a choice.
        
        Args:
            params: Call parameters including match_id, context, deadline.
        
        Returns:
            CHOOSE_PARITY_RESPONSE with the choice.
        """
        match_id = params.get("match_id")
        player_id = params.get("player_id")
        game_type = params.get("game_type")
        context = params.get("context", {})
        deadline = params.get("deadline")
        
        self.state.logger.debug("CHOOSE_PARITY_CALL_RECEIVED",
                                match_id=match_id)
        
        # Build context for strategy
        strategy_context = {
            "opponent_id": context.get("opponent_id"),
            "round_id": context.get("round_id"),
            "standings": context.get("your_standings", {}),
            "match_id": match_id
        }
        
        # Use strategy to make choice
        if self.state.strategy_manager:
            choice = self.state.strategy_manager.choose(strategy_context)
        else:
            # Fallback to random if strategy not initialized
            import random
            choice = random.choice(["even", "odd"])
        
        # Ensure lowercase
        choice = choice.lower()
        
        # Store choice in current match
        if self.state.current_match and self.state.current_match.get("match_id") == match_id:
            self.state.current_match["my_choice"] = choice
        
        self.state.logger.info("PARITY_CHOICE_MADE",
                               match_id=match_id,
                               choice=choice)
        
        response = self._create_envelope(
            "CHOOSE_PARITY_RESPONSE",
            match_id=match_id,
            player_id=self.state.player_id,
            parity_choice=choice,
            choice=choice  # Include both for compatibility
        )
        
        return response
    
    # =========================================================================
    # Game Over Handler
    # =========================================================================
    
    async def handle_game_over(self, params: dict) -> dict:
        """
        Handle GAME_OVER notification from referee.
        
        Updates history and strategy based on result.
        
        Args:
            params: Game result parameters.
        
        Returns:
            Acknowledgment.
        """
        match_id = params.get("match_id")
        game_result = params.get("game_result", {})
        
        status = game_result.get("status")
        winner_id = game_result.get("winner_player_id")
        drawn_number = game_result.get("drawn_number")
        number_parity = game_result.get("number_parity")
        choices = game_result.get("choices", {})
        reason = game_result.get("reason")
        
        # Determine my result
        if status == "DRAW":
            my_result = "DRAW"
        elif winner_id == self.state.player_id:
            my_result = "WIN"
        else:
            my_result = "LOSS"
        
        # Get my choice and opponent's choice
        my_choice = choices.get(self.state.player_id)
        opponent_id = None
        opponent_choice = None
        
        for pid, choice in choices.items():
            if pid != self.state.player_id:
                opponent_id = pid
                opponent_choice = choice
                break
        
        self.state.logger.info("GAME_OVER_RECEIVED",
                               match_id=match_id,
                               result=my_result,
                               my_choice=my_choice,
                               drawn_number=drawn_number)
        
        # Update history repository
        if self.state.history_repo and opponent_id:
            self.state.history_repo.add_match(
                match_id=match_id,
                league_id=self.state.league_id,
                opponent_id=opponent_id,
                result=my_result,
                my_choice=my_choice,
                opponent_choice=opponent_choice,
                details={
                    "drawn_number": drawn_number,
                    "number_parity": number_parity,
                    "reason": reason
                }
            )
        
        # Update strategy
        if self.state.strategy_manager:
            self.state.strategy_manager.update({
                "match_id": match_id,
                "result": my_result,
                "my_choice": my_choice,
                "opponent_id": opponent_id,
                "opponent_choice": opponent_choice,
                "details": {
                    "drawn_number": drawn_number,
                    "number_parity": number_parity
                }
            })
        
        # Clear current match
        self.state.current_match = None
        
        return {
            "status": "received",
            "match_id": match_id,
            "result": my_result
        }
    
    # =========================================================================
    # Notification Handler
    # =========================================================================
    
    async def handle_notification(self, params: dict) -> dict:
        """
        Handle general notifications from League Manager.
        
        Processes:
        - ROUND_ANNOUNCEMENT
        - LEAGUE_STANDINGS_UPDATE
        - ROUND_COMPLETED
        - LEAGUE_COMPLETED
        """
        message_type = params.get("message_type")
        
        if message_type == "ROUND_ANNOUNCEMENT":
            return await self._handle_round_announcement(params)
        
        elif message_type == "LEAGUE_STANDINGS_UPDATE":
            return await self._handle_standings_update(params)
        
        elif message_type == "ROUND_COMPLETED":
            round_id = params.get("round_id")
            self.state.logger.info("ROUND_COMPLETED_NOTIFICATION",
                                   round_id=round_id)
            return {"status": "acknowledged", "round_id": round_id}
        
        elif message_type == "LEAGUE_COMPLETED":
            champion = params.get("champion", {})
            self.state.logger.info("LEAGUE_COMPLETED_NOTIFICATION",
                                   champion=champion.get("player_id"))
            return {"status": "acknowledged", "message_type": message_type}
        
        else:
            self.state.logger.debug("NOTIFICATION_IGNORED",
                                    message_type=message_type)
            return {"status": "ignored", "message_type": message_type}
    
    async def _handle_round_announcement(self, params: dict) -> dict:
        """Handle ROUND_ANNOUNCEMENT."""
        round_id = params.get("round_id")
        matches = params.get("matches", [])
        
        # Find my matches
        my_matches = [
            m for m in matches
            if m.get("player_A_id") == self.state.player_id or
               m.get("player_B_id") == self.state.player_id
        ]
        
        self.state.logger.info("ROUND_ANNOUNCEMENT_RECEIVED",
                               round_id=round_id,
                               my_matches=len(my_matches))
        
        return {
            "status": "acknowledged",
            "round_id": round_id,
            "matches_count": len(my_matches)
        }
    
    async def _handle_standings_update(self, params: dict) -> dict:
        """Handle LEAGUE_STANDINGS_UPDATE."""
        round_id = params.get("round_id")
        standings = params.get("standings", [])
        
        # Find my position
        my_standing = None
        for standing in standings:
            if standing.get("player_id") == self.state.player_id:
                my_standing = standing
                break
        
        if my_standing:
            self.state.logger.info("STANDINGS_UPDATE_RECEIVED",
                                   round_id=round_id,
                                   rank=my_standing.get("rank"),
                                   points=my_standing.get("points"))
        
        return {
            "status": "acknowledged",
            "round_id": round_id,
            "my_rank": my_standing.get("rank") if my_standing else None
        }
    
    # =========================================================================
    # Query Handlers
    # =========================================================================
    
    async def get_stats(self) -> dict:
        """Get player statistics."""
        if self.state.history_repo:
            stats = self.state.history_repo.get_stats()
            win_rate = self.state.history_repo.get_win_rate()
            return {
                "player_id": self.state.player_id,
                "stats": stats,
                "win_rate": round(win_rate, 3),
                "strategy": self.state.strategy_type
            }
        else:
            return {
                "player_id": self.state.player_id,
                "stats": {},
                "win_rate": 0,
                "strategy": self.state.strategy_type
            }
    
    async def get_history(self, params: dict) -> dict:
        """Get match history."""
        limit = params.get("limit", 10)
        
        if self.state.history_repo:
            matches = self.state.history_repo.get_matches(limit=limit)
            return {
                "player_id": self.state.player_id,
                "matches": matches
            }
        else:
            return {
                "player_id": self.state.player_id,
                "matches": []
            }

