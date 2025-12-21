"""
Referee Handlers - Match management handlers.

Implements the complete match flow:
1. GAME_INVITATION to players
2. Wait for GAME_JOIN_ACK
3. CHOOSE_PARITY_CALL to collect choices
4. Draw number and determine winner
5. GAME_OVER to players
6. MATCH_RESULT_REPORT to League Manager

Based on Chapters 3 and 8 of the League Protocol specification.
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

import httpx

from game_logic import EvenOddGame, GameState, MatchResult

if TYPE_CHECKING:
    from main import RefereeState


class RefereeHandlers:
    """Handlers for referee match operations."""
    
    def __init__(self, state: "RefereeState"):
        self.state = state
        self.game = EvenOddGame()
    
    def _create_envelope(self, message_type: str, **extra_fields) -> dict:
        """Create a protocol envelope."""
        envelope = {
            "protocol": "league.v2",
            "message_type": message_type,
            "sender": f"referee:{self.state.referee_id}" if self.state.referee_id else "referee:UNREGISTERED",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self.state.auth_token:
            envelope["auth_token"] = self.state.auth_token
        
        envelope.update(extra_fields)
        return envelope
    
    # =========================================================================
    # Notification Handler
    # =========================================================================
    
    async def handle_notification(self, params: dict) -> dict:
        """
        Handle incoming notifications from League Manager.
        
        Processes:
        - ROUND_ANNOUNCEMENT: Store match assignments and player endpoints
        """
        message_type = params.get("message_type")
        
        if message_type == "ROUND_ANNOUNCEMENT":
            return await self._handle_round_announcement(params)
        else:
            self.state.logger.debug("NOTIFICATION_IGNORED", 
                                    message_type=message_type)
            return {"status": "ignored", "message_type": message_type}
    
    async def _handle_round_announcement(self, params: dict) -> dict:
        """Handle ROUND_ANNOUNCEMENT from League Manager."""
        round_id = params.get("round_id")
        matches = params.get("matches", [])
        
        self.state.logger.info("ROUND_ANNOUNCEMENT_RECEIVED",
                               round_id=round_id,
                               num_matches=len(matches))
        
        # Store player endpoints from the announcement
        # In a real system, we'd get these from the league manager
        # For now, we'll use the configured agents
        agents_config = self.state.config_loader.load_agents()
        for player in agents_config.players:
            self.state.player_endpoints[player.player_id] = player.default_endpoint
        
        # Process matches assigned to this referee
        my_matches = [m for m in matches 
                      if m.get("referee_id") == self.state.referee_id]
        
        # Start running each match
        results = []
        for match_info in my_matches:
            match_id = match_info.get("match_id")
            player_a = match_info.get("player_A_id")
            player_b = match_info.get("player_B_id")
            
            # Initialize match state
            self.state.active_matches[match_id] = {
                "match_id": match_id,
                "round_id": round_id,
                "player_a": player_a,
                "player_b": player_b,
                "state": GameState.WAITING_FOR_PLAYERS.value,
                "choices": {},
                "result": None
            }
            
            # Run match asynchronously
            asyncio.create_task(self._run_match_async(match_id, round_id, 
                                                       player_a, player_b))
            results.append({"match_id": match_id, "status": "started"})
        
        return {
            "status": "accepted",
            "round_id": round_id,
            "matches_started": len(results)
        }
    
    # =========================================================================
    # Match Execution
    # =========================================================================
    
    async def run_match(self, params: dict) -> dict:
        """
        Manually run a match (for testing).
        
        Args:
            params: Match parameters (match_id, player_a, player_b, round_id).
        """
        match_id = params.get("match_id")
        player_a = params.get("player_a")
        player_b = params.get("player_b")
        round_id = params.get("round_id", 1)
        
        if not all([match_id, player_a, player_b]):
            raise ValueError("Missing required parameters")
        
        # Ensure we have player endpoints
        agents_config = self.state.config_loader.load_agents()
        for player in agents_config.players:
            self.state.player_endpoints[player.player_id] = player.default_endpoint
        
        # Run the match
        result = await self._run_match_async(match_id, round_id, player_a, player_b)
        return self.game.result_to_dict(result)
    
    async def _run_match_async(
        self, 
        match_id: str, 
        round_id: int,
        player_a: str, 
        player_b: str
    ):
        """
        Run a complete match asynchronously.
        
        Implements the match flow from Ch. 3.2:
        1. Send GAME_INVITATION to both players
        2. Wait for GAME_JOIN_ACK
        3. Call choose_parity for both players
        4. Draw number and determine winner
        5. Send GAME_OVER to players
        6. Send MATCH_RESULT_REPORT to League Manager
        """
        self.state.logger.info("MATCH_STARTING",
                               match_id=match_id,
                               player_a=player_a,
                               player_b=player_b)
        
        conversation_id = f"conv-{match_id}-{datetime.utcnow().strftime('%H%M%S')}"
        
        try:
            # Step 1: Send GAME_INVITATION to both players
            self.state.logger.debug("SENDING_INVITATIONS", match_id=match_id)
            
            invite_results = await self._send_game_invitations(
                match_id, round_id, player_a, player_b, conversation_id
            )
            
            # Check if both players accepted
            if not all(r.get("accepted") for r in invite_results.values()):
                # Handle player not responding
                for pid, result in invite_results.items():
                    if not result.get("accepted"):
                        self.state.logger.warning("PLAYER_NOT_RESPONDING",
                                                  match_id=match_id,
                                                  player_id=pid)
                        # Create technical loss for non-responding player
                        game_result = self.game.create_technical_loss(
                            player_a, player_b, pid,
                            f"Player {pid} did not respond to invitation"
                        )
                        await self._finish_match(match_id, round_id, player_a, 
                                                  player_b, game_result, conversation_id)
                        return game_result
            
            # Step 2: Update state to COLLECTING_CHOICES
            if match_id in self.state.active_matches:
                self.state.active_matches[match_id]["state"] = GameState.COLLECTING_CHOICES.value
            
            # Step 3: Call choose_parity for both players
            self.state.logger.debug("COLLECTING_CHOICES", match_id=match_id)
            
            choices = await self._collect_choices(
                match_id, round_id, player_a, player_b, conversation_id
            )
            
            # Handle timeouts
            for pid, choice in choices.items():
                if choice is None:
                    self.state.logger.warning("CHOICE_TIMEOUT",
                                              match_id=match_id,
                                              player_id=pid)
                    game_result = self.game.create_technical_loss(
                        player_a, player_b, pid,
                        f"Player {pid} timed out on choice"
                    )
                    await self._finish_match(match_id, round_id, player_a, 
                                              player_b, game_result, conversation_id)
                    return game_result
            
            # Step 4: Draw number and determine winner
            self.state.logger.debug("DETERMINING_WINNER", match_id=match_id)
            
            game_result = self.game.determine_winner(
                player_a, player_b,
                choices[player_a], choices[player_b]
            )
            
            self.state.logger.info("MATCH_RESULT",
                                   match_id=match_id,
                                   winner=game_result.winner_player_id,
                                   number=game_result.drawn_number,
                                   parity=game_result.number_parity)
            
            # Step 5 & 6: Finish match (send GAME_OVER and MATCH_RESULT_REPORT)
            await self._finish_match(match_id, round_id, player_a, 
                                      player_b, game_result, conversation_id)
            
            return game_result
            
        except Exception as e:
            self.state.logger.error("MATCH_ERROR",
                                    match_id=match_id,
                                    error=str(e))
            raise
    
    # =========================================================================
    # Game Invitation (Step 1)
    # =========================================================================
    
    async def _send_game_invitations(
        self,
        match_id: str,
        round_id: int,
        player_a: str,
        player_b: str,
        conversation_id: str
    ) -> Dict[str, dict]:
        """Send GAME_INVITATION to both players and wait for ACK."""
        results = {}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Send invitations in parallel
            tasks = {
                player_a: self._send_invitation(
                    client, match_id, round_id, player_a, player_b, 
                    "PLAYER_A", conversation_id
                ),
                player_b: self._send_invitation(
                    client, match_id, round_id, player_b, player_a,
                    "PLAYER_B", conversation_id
                )
            }
            
            for player_id, task in tasks.items():
                try:
                    result = await task
                    results[player_id] = result
                except Exception as e:
                    results[player_id] = {"accepted": False, "error": str(e)}
        
        return results
    
    async def _send_invitation(
        self,
        client: httpx.AsyncClient,
        match_id: str,
        round_id: int,
        player_id: str,
        opponent_id: str,
        role: str,
        conversation_id: str
    ) -> dict:
        """Send GAME_INVITATION to a single player."""
        endpoint = self.state.player_endpoints.get(player_id)
        if not endpoint:
            return {"accepted": False, "error": "Unknown player endpoint"}
        
        invitation = self._create_envelope(
            "GAME_INVITATION",
            league_id=self.state.league_id,
            round_id=round_id,
            match_id=match_id,
            game_type=self.state.league_config.game_type,
            role_in_match=role,
            opponent_id=opponent_id,
            conversation_id=conversation_id
        )
        
        payload = {
            "jsonrpc": "2.0",
            "method": "game_invitation",
            "params": invitation,
            "id": 1
        }
        
        try:
            response = await client.post(endpoint, json=payload)
            
            if response.status_code == 200:
                result = response.json().get("result", {})
                accepted = result.get("accept", result.get("accepted", True))
                
                self.state.logger.log_message_sent(
                    "GAME_INVITATION", player_id,
                    match_id=match_id, accepted=accepted
                )
                
                return {"accepted": accepted}
            else:
                return {"accepted": False, "error": f"HTTP {response.status_code}"}
                
        except httpx.TimeoutException:
            return {"accepted": False, "error": "Timeout"}
        except Exception as e:
            return {"accepted": False, "error": str(e)}
    
    # =========================================================================
    # Choice Collection (Step 3)
    # =========================================================================
    
    async def _collect_choices(
        self,
        match_id: str,
        round_id: int,
        player_a: str,
        player_b: str,
        conversation_id: str
    ) -> Dict[str, Optional[str]]:
        """Collect parity choices from both players."""
        choices = {}
        
        # Get current standings for context
        standings_a = {"wins": 0, "losses": 0, "draws": 0}
        standings_b = {"wins": 0, "losses": 0, "draws": 0}
        
        async with httpx.AsyncClient(timeout=35.0) as client:
            # Collect choices in parallel
            tasks = {
                player_a: self._request_choice(
                    client, match_id, round_id, player_a, player_b,
                    standings_a, conversation_id
                ),
                player_b: self._request_choice(
                    client, match_id, round_id, player_b, player_a,
                    standings_b, conversation_id
                )
            }
            
            for player_id, task in tasks.items():
                try:
                    choice = await task
                    choices[player_id] = choice
                except Exception as e:
                    self.state.logger.warning("CHOICE_COLLECTION_ERROR",
                                              player_id=player_id,
                                              error=str(e))
                    choices[player_id] = None
        
        return choices
    
    async def _request_choice(
        self,
        client: httpx.AsyncClient,
        match_id: str,
        round_id: int,
        player_id: str,
        opponent_id: str,
        standings: dict,
        conversation_id: str
    ) -> Optional[str]:
        """Request parity choice from a single player."""
        endpoint = self.state.player_endpoints.get(player_id)
        if not endpoint:
            return None
        
        # Calculate deadline (30 seconds from now)
        move_timeout = self.state.system_config.timeouts.move_timeout_sec
        deadline = datetime.utcnow()
        deadline_str = deadline.isoformat() + "Z"
        
        call_msg = self._create_envelope(
            "CHOOSE_PARITY_CALL",
            match_id=match_id,
            player_id=player_id,
            game_type=self.state.league_config.game_type,
            context={
                "opponent_id": opponent_id,
                "round_id": round_id,
                "your_standings": standings
            },
            deadline=deadline_str,
            conversation_id=conversation_id
        )
        
        payload = {
            "jsonrpc": "2.0",
            "method": "choose_parity",
            "params": call_msg,
            "id": 2
        }
        
        try:
            response = await client.post(endpoint, json=payload)
            
            if response.status_code == 200:
                result = response.json().get("result", {})
                choice = result.get("parity_choice", result.get("choice"))
                
                if choice and self.game.validate_choice(choice):
                    normalized = self.game.normalize_choice(choice)
                    
                    self.state.logger.debug("CHOICE_RECEIVED",
                                            player_id=player_id,
                                            choice=normalized)
                    
                    return normalized
                else:
                    self.state.logger.warning("INVALID_CHOICE",
                                              player_id=player_id,
                                              choice=choice)
                    return None
            else:
                return None
                
        except httpx.TimeoutException:
            self.state.logger.warning("CHOICE_TIMEOUT", player_id=player_id)
            return None
        except Exception as e:
            self.state.logger.error("CHOICE_ERROR", 
                                    player_id=player_id, 
                                    error=str(e))
            return None
    
    # =========================================================================
    # Finish Match (Steps 5 & 6)
    # =========================================================================
    
    async def _finish_match(
        self,
        match_id: str,
        round_id: int,
        player_a: str,
        player_b: str,
        result,  # GameResult
        conversation_id: str
    ):
        """
        Finish a match by sending results.
        
        1. Send GAME_OVER to both players
        2. Send MATCH_RESULT_REPORT to League Manager
        """
        # Update match state
        if match_id in self.state.active_matches:
            self.state.active_matches[match_id]["state"] = GameState.FINISHED.value
            self.state.active_matches[match_id]["result"] = self.game.result_to_dict(result)
        
        # Step 5: Send GAME_OVER to both players
        await self._send_game_over(match_id, player_a, player_b, result, conversation_id)
        
        # Step 6: Send MATCH_RESULT_REPORT to League Manager
        await self._send_match_result_report(match_id, round_id, result, conversation_id)
        
        # Save match data
        match_data = self.state.match_repo.load(match_id)
        if match_data:
            self.state.match_repo.set_result(
                match_id,
                result.status.value,
                result.winner_player_id,
                {
                    "drawn_number": result.drawn_number,
                    "number_parity": result.number_parity,
                    "choices": result.choices
                }
            )
        
        self.state.logger.info("MATCH_COMPLETED",
                               match_id=match_id,
                               winner=result.winner_player_id,
                               status=result.status.value)
    
    async def _send_game_over(
        self,
        match_id: str,
        player_a: str,
        player_b: str,
        result,  # GameResult
        conversation_id: str
    ):
        """Send GAME_OVER to both players."""
        game_over = self._create_envelope(
            "GAME_OVER",
            match_id=match_id,
            game_type=self.state.league_config.game_type,
            conversation_id=conversation_id,
            game_result={
                "status": result.status.value,
                "winner_player_id": result.winner_player_id,
                "drawn_number": result.drawn_number,
                "number_parity": result.number_parity,
                "choices": result.choices,
                "reason": result.reason
            }
        )
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for player_id in [player_a, player_b]:
                endpoint = self.state.player_endpoints.get(player_id)
                if not endpoint:
                    continue
                
                payload = {
                    "jsonrpc": "2.0",
                    "method": "notify_game_over",
                    "params": game_over,
                    "id": None
                }
                
                try:
                    await client.post(endpoint, json=payload)
                    self.state.logger.log_message_sent(
                        "GAME_OVER", player_id, match_id=match_id
                    )
                except Exception as e:
                    self.state.logger.warning("GAME_OVER_SEND_FAILED",
                                              player_id=player_id,
                                              error=str(e))
    
    async def _send_match_result_report(
        self,
        match_id: str,
        round_id: int,
        result,  # GameResult
        conversation_id: str
    ):
        """Send MATCH_RESULT_REPORT to League Manager."""
        report = self._create_envelope(
            "MATCH_RESULT_REPORT",
            league_id=self.state.league_id,
            round_id=round_id,
            match_id=match_id,
            game_type=self.state.league_config.game_type,
            conversation_id=f"conv-{match_id}-report",
            result={
                "winner": result.winner_player_id,
                "score": result.scores,
                "details": {
                    "drawn_number": result.drawn_number,
                    "choices": result.choices
                }
            }
        )
        
        payload = {
            "jsonrpc": "2.0",
            "method": "report_match_result",
            "params": report,
            "id": 100
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self.state.league_manager_endpoint,
                    json=payload
                )
                
                if response.status_code == 200:
                    self.state.logger.info("MATCH_RESULT_REPORTED",
                                           match_id=match_id)
                else:
                    self.state.logger.warning("MATCH_RESULT_REPORT_FAILED",
                                              match_id=match_id,
                                              status_code=response.status_code)
                    
            except Exception as e:
                self.state.logger.error("MATCH_RESULT_REPORT_ERROR",
                                        match_id=match_id,
                                        error=str(e))
    
    # =========================================================================
    # Query Handler
    # =========================================================================
    
    async def get_match_state(self, params: dict) -> dict:
        """Get the current state of a match."""
        match_id = params.get("match_id")
        
        if match_id in self.state.active_matches:
            return self.state.active_matches[match_id]
        
        # Try loading from repository
        match_data = self.state.match_repo.load(match_id)
        if match_data:
            return match_data
        
        raise ValueError(f"Match not found: {match_id}")

