"""
League Manager Handlers - Message handlers for the league manager.

Implements handlers for:
- Referee registration (Ch. 4.1)
- Player registration (Ch. 4.2)
- Match result reports
- League queries
- Round announcements

Based on the League Protocol specification.
"""

import secrets
import httpx
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import LeagueState


class LeagueHandlers:
    """Handlers for league manager operations."""
    
    def __init__(self, state: "LeagueState"):
        self.state = state
    
    def _generate_auth_token(self) -> str:
        """Generate a secure authentication token."""
        token_length = self.state.system_config.security.token_length
        return f"tok_{secrets.token_hex(token_length // 2)}"
    
    def _create_envelope(self, message_type: str, **extra_fields) -> dict:
        """Create a protocol envelope."""
        return {
            "protocol": "league.v2",
            "message_type": message_type,
            "sender": "league_manager",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "league_id": self.state.league_id,
            **extra_fields
        }
    
    # =========================================================================
    # Registration Handlers (Ch. 4.1, 4.2)
    # =========================================================================
    
    async def handle_register_referee(self, params: dict) -> dict:
        """
        Handle REFEREE_REGISTER_REQUEST.
        
        Assigns a unique referee_id and auth_token.
        
        Args:
            params: Request parameters containing referee_meta.
        
        Returns:
            REFEREE_REGISTER_RESPONSE envelope.
        """
        # Validate required fields
        referee_meta = params.get("referee_meta")
        if not referee_meta:
            raise ValueError("Missing required field: referee_meta")
        
        display_name = referee_meta.get("display_name")
        if not display_name:
            raise ValueError("Missing required field: referee_meta.display_name")
        
        contact_endpoint = referee_meta.get("contact_endpoint")
        if not contact_endpoint:
            raise ValueError("Missing required field: referee_meta.contact_endpoint")
        
        game_types = referee_meta.get("game_types", [])
        version = referee_meta.get("version", "1.0.0")
        max_concurrent = referee_meta.get("max_concurrent_matches", 2)
        
        # Get conversation_id from request
        conversation_id = params.get("conversation_id", f"conv-ref-{display_name.lower().replace(' ', '-')}-reg")
        
        # Check if referee is already registered by endpoint
        for ref_id, ref_data in self.state.registered_referees.items():
            if ref_data["endpoint"] == contact_endpoint:
                # Already registered, return existing info
                self.state.logger.info("REFEREE_ALREADY_REGISTERED",
                                       referee_id=ref_id,
                                       display_name=display_name)
                return self._create_envelope(
                    "REFEREE_REGISTER_RESPONSE",
                    conversation_id=conversation_id,
                    status="ACCEPTED",
                    referee_id=ref_id,
                    auth_token=ref_data["auth_token"],
                    reason="Already registered"
                )
        
        # Generate new referee ID
        self.state._referee_counter += 1
        referee_id = f"REF{self.state._referee_counter:02d}"
        
        # Generate auth token
        auth_token = self._generate_auth_token()
        
        # Store registration
        self.state.registered_referees[referee_id] = {
            "referee_id": referee_id,
            "display_name": display_name,
            "endpoint": contact_endpoint,
            "version": version,
            "game_types": game_types,
            "max_concurrent_matches": max_concurrent,
            "auth_token": auth_token,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            "active": True
        }
        
        self.state.logger.info("REFEREE_REGISTERED",
                               referee_id=referee_id,
                               display_name=display_name,
                               game_types=game_types)
        
        return self._create_envelope(
            "REFEREE_REGISTER_RESPONSE",
            conversation_id=conversation_id,
            status="ACCEPTED",
            referee_id=referee_id,
            auth_token=auth_token,
            reason=None
        )
    
    async def handle_register_player(self, params: dict) -> dict:
        """
        Handle LEAGUE_REGISTER_REQUEST.
        
        Assigns a unique player_id and auth_token.
        
        Args:
            params: Request parameters containing player_meta.
        
        Returns:
            LEAGUE_REGISTER_RESPONSE envelope.
        """
        # Validate required fields
        player_meta = params.get("player_meta")
        if not player_meta:
            raise ValueError("Missing required field: player_meta")
        
        display_name = player_meta.get("display_name")
        if not display_name:
            raise ValueError("Missing required field: player_meta.display_name")
        
        contact_endpoint = player_meta.get("contact_endpoint")
        if not contact_endpoint:
            raise ValueError("Missing required field: player_meta.contact_endpoint")
        
        game_types = player_meta.get("game_types", [])
        version = player_meta.get("version", "1.0.0")
        
        # Get conversation_id from request
        conversation_id = params.get("conversation_id", f"conv-player-{display_name.lower().replace(' ', '-')}-reg")
        
        # Check if player is already registered by endpoint
        for player_id, player_data in self.state.registered_players.items():
            if player_data["endpoint"] == contact_endpoint:
                # Already registered, return existing info
                self.state.logger.info("PLAYER_ALREADY_REGISTERED",
                                       player_id=player_id,
                                       display_name=display_name)
                return self._create_envelope(
                    "LEAGUE_REGISTER_RESPONSE",
                    conversation_id=conversation_id,
                    status="ACCEPTED",
                    player_id=player_id,
                    auth_token=player_data["auth_token"],
                    reason="Already registered"
                )
        
        # Generate new player ID
        self.state._player_counter += 1
        player_id = f"P{self.state._player_counter:02d}"
        
        # Generate auth token
        auth_token = self._generate_auth_token()
        
        # Store registration
        self.state.registered_players[player_id] = {
            "player_id": player_id,
            "display_name": display_name,
            "endpoint": contact_endpoint,
            "version": version,
            "game_types": game_types,
            "auth_token": auth_token,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            "active": True
        }
        
        # Note: Standings are initialized when the league starts (handle_start_league)
        # This ensures a clean slate for each league run
        
        self.state.logger.info("PLAYER_REGISTERED",
                               player_id=player_id,
                               display_name=display_name,
                               game_types=game_types)
        
        return self._create_envelope(
            "LEAGUE_REGISTER_RESPONSE",
            conversation_id=conversation_id,
            status="ACCEPTED",
            player_id=player_id,
            auth_token=auth_token,
            reason=None
        )
    
    # =========================================================================
    # Match Result Handler
    # =========================================================================
    
    async def handle_match_result_report(self, params: dict) -> dict:
        """
        Handle MATCH_RESULT_REPORT from a referee.
        
        Updates standings and tracks round progress.
        
        Args:
            params: Match result parameters.
        
        Returns:
            Acknowledgment envelope.
        """
        # Validate auth token
        auth_token = params.get("auth_token")
        sender = params.get("sender", "")
        
        if sender.startswith("referee:"):
            referee_id = sender.split(":")[1]
            if referee_id in self.state.registered_referees:
                expected_token = self.state.registered_referees[referee_id]["auth_token"]
                if auth_token != expected_token:
                    raise ValueError("Invalid auth_token")
        
        # Extract result data
        match_id = params.get("match_id")
        round_id = params.get("round_id")
        result = params.get("result", {})
        
        winner = result.get("winner")
        score = result.get("score", {})
        
        self.state.logger.info("MATCH_RESULT_RECEIVED",
                               match_id=match_id,
                               round_id=round_id,
                               winner=winner)
        
        # Update standings for each player
        for player_id, points in score.items():
            if player_id in self.state.registered_players:
                display_name = self.state.registered_players[player_id]["display_name"]
                
                if winner == player_id:
                    match_result = "WIN"
                elif winner is None:
                    match_result = "DRAW"
                else:
                    match_result = "LOSS"
                
                self.state.standings_repo.update_player(
                    player_id=player_id,
                    display_name=display_name,
                    result=match_result,
                    points=points
                )
        
        # Track round progress
        self.state.matches_completed_this_round += 1
        
        # Check if round is complete
        matches_per_round = len(self.state.registered_players) // 2
        if self.state.matches_completed_this_round >= matches_per_round:
            self.state.standings_repo.increment_rounds_completed()
            self.state.logger.info("ROUND_COMPLETED",
                                   round_id=self.state.current_round,
                                   matches_completed=self.state.matches_completed_this_round)
            
            # Broadcast ROUND_COMPLETED message
            await self._broadcast_round_completed()
            
            # Broadcast standings update
            await self._broadcast_standings_update()
            
            # Check if league is complete (all rounds played)
            if self.state.current_round >= len(self.state.schedule):
                await self._broadcast_league_completed()
        
        return self._create_envelope(
            "MATCH_RESULT_ACK",
            match_id=match_id,
            status="RECEIVED"
        )
    
    # =========================================================================
    # League Control Handlers
    # =========================================================================
    
    async def handle_start_league(self, params: dict) -> dict:
        """
        Start the league and create the match schedule.
        
        Uses Round-Robin scheduling for all registered players.
        
        Returns:
            League start confirmation with schedule.
        """
        player_ids = list(self.state.registered_players.keys())
        
        if len(player_ids) < 2:
            raise ValueError("Need at least 2 players to start league")
        
        # Reset standings for fresh start
        self.state.standings_repo.reset()
        self.state.logger.info("STANDINGS_RESET", league_id=self.state.league_id)
        
        # Re-initialize all players in standings with 0 stats
        for player_id, player_data in self.state.registered_players.items():
            standings = self.state.standings_repo.load()
            standings_list = standings.get("standings", [])
            standings_list.append({
                "player_id": player_id,
                "display_name": player_data["display_name"],
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "points": 0,
                "rank": len(standings_list) + 1
            })
            standings["standings"] = standings_list
            self.state.standings_repo.save(standings)
        
        # Create Round-Robin schedule
        self.state.schedule = self.state.scheduler.create_schedule(player_ids)
        self.state.current_round = 0
        
        self.state.logger.info("LEAGUE_STARTED",
                               num_players=len(player_ids),
                               total_rounds=len(self.state.schedule),
                               total_matches=sum(len(r) for r in self.state.schedule))
        
        return self._create_envelope(
            "LEAGUE_STARTED",
            num_players=len(player_ids),
            players=player_ids,
            total_rounds=len(self.state.schedule),
            schedule_preview=[
                {
                    "round_id": i + 1,
                    "matches": [
                        {"match_id": f"R{i+1}M{j+1}", 
                         "player_A_id": match[0], 
                         "player_B_id": match[1]}
                        for j, match in enumerate(round_matches)
                    ]
                }
                for i, round_matches in enumerate(self.state.schedule)
            ]
        )
    
    async def handle_announce_round(self, params: dict) -> dict:
        """
        Announce a new round to all players.
        
        Sends ROUND_ANNOUNCEMENT to all registered players.
        
        Returns:
            Announcement confirmation.
        """
        # Move to next round
        self.state.current_round += 1
        self.state.matches_completed_this_round = 0
        
        round_idx = self.state.current_round - 1
        
        if round_idx >= len(self.state.schedule):
            raise ValueError("No more rounds in schedule")
        
        round_matches = self.state.schedule[round_idx]
        
        # Select referees for this round
        referee_ids = list(self.state.registered_referees.keys())
        if not referee_ids:
            raise ValueError("No referees registered")
        
        # Build match list for announcement - distribute matches across referees
        # Each referee gets 1 match per round (round-robin assignment)
        matches = []
        for i, (player_a, player_b) in enumerate(round_matches):
            match_id = f"R{self.state.current_round}M{i + 1}"
            # Assign each match to a different referee (cycling through available referees)
            referee_id = referee_ids[i % len(referee_ids)]
            referee_endpoint = self.state.registered_referees[referee_id]["endpoint"]
            matches.append({
                "match_id": match_id,
                "game_type": self.state.league_config.game_type,
                "player_A_id": player_a,
                "player_B_id": player_b,
                "referee_id": referee_id,
                "referee_endpoint": referee_endpoint
            })
        
        # Create announcement message
        announcement = self._create_envelope(
            "ROUND_ANNOUNCEMENT",
            round_id=self.state.current_round,
            conversation_id=f"conv-round-{self.state.current_round}-announce",
            matches=matches
        )
        
        self.state.logger.info("ROUND_ANNOUNCEMENT_SENT",
                               round_id=self.state.current_round,
                               num_matches=len(matches))
        
        # Send to all players
        notification_results = await self._broadcast_to_players(announcement)
        
        # Notify all referees who have matches in this round
        notified_referees = set()
        for match in matches:
            ref_id = match["referee_id"]
            if ref_id not in notified_referees:
                await self._notify_referee(ref_id, announcement)
                notified_referees.add(ref_id)
        
        return self._create_envelope(
            "ROUND_ANNOUNCEMENT_COMPLETE",
            round_id=self.state.current_round,
            matches=matches,
            notifications_sent=len(notification_results)
        )
    
    async def handle_league_query(self, params: dict) -> dict:
        """
        Handle league state queries.
        
        Supports query types:
        - GET_STANDINGS: Current standings
        - GET_SCHEDULE: Match schedule
        - GET_PLAYERS: Registered players
        """
        # Validate auth token
        auth_token = params.get("auth_token")
        query_type = params.get("query_type", "GET_STANDINGS")
        
        if query_type == "GET_STANDINGS":
            standings = self.state.standings_repo.load()
            return self._create_envelope(
                "LEAGUE_STANDINGS_UPDATE",
                round_id=self.state.current_round,
                standings=standings.get("standings", [])
            )
        
        elif query_type == "GET_SCHEDULE":
            return self._create_envelope(
                "LEAGUE_SCHEDULE",
                total_rounds=len(self.state.schedule),
                current_round=self.state.current_round,
                schedule=[
                    {
                        "round_id": i + 1,
                        "matches": [
                            {"player_A": m[0], "player_B": m[1]}
                            for m in round_matches
                        ]
                    }
                    for i, round_matches in enumerate(self.state.schedule)
                ]
            )
        
        elif query_type == "GET_PLAYERS":
            return self._create_envelope(
                "PLAYER_LIST",
                players=[
                    {
                        "player_id": pid,
                        "display_name": pdata["display_name"],
                        "active": pdata["active"]
                    }
                    for pid, pdata in self.state.registered_players.items()
                ]
            )
        
        elif query_type == "GET_STATUS":
            total_rounds = len(self.state.schedule) if self.state.schedule else 0
            is_complete = self.state.current_round >= total_rounds and total_rounds > 0
            
            standings = self.state.standings_repo.load()
            standings_list = standings.get("standings", [])
            champion = None
            if is_complete and standings_list:
                champion = max(standings_list, key=lambda x: x.get("points", 0))
            
            return self._create_envelope(
                "LEAGUE_STATUS",
                current_round=self.state.current_round,
                total_rounds=total_rounds,
                is_complete=is_complete,
                champion={
                    "player_id": champion.get("player_id"),
                    "display_name": champion.get("display_name"),
                    "points": champion.get("points", 0)
                } if champion else None
            )
        
        else:
            raise ValueError(f"Unknown query_type: {query_type}")
    
    # =========================================================================
    # Communication Helpers
    # =========================================================================
    
    async def _broadcast_to_players(self, message: dict, method: str = "notify_round") -> list:
        """Broadcast a message to all registered players."""
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for player_id, player_data in self.state.registered_players.items():
                if not player_data["active"]:
                    continue
                
                endpoint = player_data["endpoint"]
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": message,
                        "id": 10  # Round announcement ID
                    }
                    
                    response = await client.post(endpoint, json=payload)
                    results.append({
                        "player_id": player_id,
                        "status": "sent",
                        "status_code": response.status_code
                    })
                    
                    self.state.logger.debug("MESSAGE_SENT",
                                            recipient=player_id,
                                            message_type=message.get("message_type"))
                    
                except Exception as e:
                    results.append({
                        "player_id": player_id,
                        "status": "failed",
                        "error": str(e)
                    })
                    self.state.logger.warning("MESSAGE_SEND_FAILED",
                                              recipient=player_id,
                                              error=str(e))
        
        return results
    
    async def _notify_referee(self, referee_id: str, message: dict, method: str = "notify_round") -> bool:
        """Send a notification to a specific referee."""
        if referee_id not in self.state.registered_referees:
            return False
        
        referee_data = self.state.registered_referees[referee_id]
        endpoint = referee_data["endpoint"]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": message,
                    "id": 10
                }
                await client.post(endpoint, json=payload)
                return True
            except Exception as e:
                self.state.logger.warning("REFEREE_NOTIFY_FAILED",
                                          referee_id=referee_id,
                                          error=str(e))
                return False
    
    async def _broadcast_round_completed(self) -> None:
        """Broadcast ROUND_COMPLETED message to all players and referees."""
        # Calculate next round
        next_round_id = self.state.current_round + 1 if self.state.current_round < len(self.state.schedule) else None

        # Calculate summary statistics for this round
        # Note: In a full implementation, we'd track wins/draws/technical_losses per round
        matches_per_round = len(self.state.registered_players) // 2

        message = self._create_envelope(
            "ROUND_COMPLETED",
            conversation_id=f"conv-round-{self.state.current_round}-complete",
            round_id=self.state.current_round,
            matches_completed=self.state.matches_completed_this_round,
            next_round_id=next_round_id,
            summary={
                "total_matches": matches_per_round,
                "wins": self.state.matches_completed_this_round,  # Approximate - each match has a winner
                "draws": 0,
                "technical_losses": 0
            }
        )
        
        # Send to all players using notify_round_completed method
        await self._broadcast_round_completed_to_players(message)
        
        # Also notify all referees
        for referee_id in self.state.registered_referees.keys():
            await self._notify_referee_round_completed(referee_id, message)
        
        self.state.logger.info("ROUND_COMPLETED_BROADCAST",
                               round_id=self.state.current_round,
                               next_round_id=next_round_id)
    
    async def _broadcast_round_completed_to_players(self, message: dict) -> list:
        """Broadcast ROUND_COMPLETED using notify_round_completed method."""
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for player_id, player_data in self.state.registered_players.items():
                if not player_data["active"]:
                    continue
                
                endpoint = player_data["endpoint"]
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "notify_round_completed",
                        "params": message,
                        "id": 1402
                    }
                    
                    response = await client.post(endpoint, json=payload)
                    results.append({
                        "player_id": player_id,
                        "status": "sent",
                        "status_code": response.status_code
                    })
                    
                except Exception as e:
                    results.append({
                        "player_id": player_id,
                        "status": "failed",
                        "error": str(e)
                    })
        
        return results
    
    async def _notify_referee_round_completed(self, referee_id: str, message: dict) -> bool:
        """Send ROUND_COMPLETED to a specific referee."""
        if referee_id not in self.state.registered_referees:
            return False
        
        referee_data = self.state.registered_referees[referee_id]
        endpoint = referee_data["endpoint"]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "notify_round_completed",
                    "params": message,
                    "id": 1402
                }
                await client.post(endpoint, json=payload)
                return True
            except Exception as e:
                self.state.logger.warning("REFEREE_ROUND_COMPLETED_FAILED",
                                          referee_id=referee_id,
                                          error=str(e))
                return False
    
    async def _broadcast_standings_update(self) -> None:
        """Broadcast current standings to all players."""
        standings = self.state.standings_repo.load()
        
        message = self._create_envelope(
            "LEAGUE_STANDINGS_UPDATE",
            conversation_id=f"conv-round-{self.state.current_round}-standings",
            round_id=self.state.current_round,
            standings=standings.get("standings", [])
        )
        
        # Send using update_standings method
        await self._broadcast_standings_to_players(message)
        
        self.state.logger.info("STANDINGS_UPDATE_BROADCAST",
                               round_id=self.state.current_round)
    
    async def _broadcast_standings_to_players(self, message: dict) -> list:
        """Broadcast standings using update_standings method."""
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for player_id, player_data in self.state.registered_players.items():
                if not player_data["active"]:
                    continue
                
                endpoint = player_data["endpoint"]
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "update_standings",
                        "params": message,
                        "id": 1401
                    }
                    
                    response = await client.post(endpoint, json=payload)
                    results.append({
                        "player_id": player_id,
                        "status": "sent",
                        "status_code": response.status_code
                    })
                    
                except Exception as e:
                    results.append({
                        "player_id": player_id,
                        "status": "failed",
                        "error": str(e)
                    })
        
        return results
    
    async def _broadcast_league_completed(self) -> None:
        """Broadcast LEAGUE_COMPLETED message to all players and referees."""
        standings = self.state.standings_repo.load()
        standings_list = standings.get("standings", [])
        
        # Determine champion (player with most points)
        champion = None
        if standings_list:
            champion = max(standings_list, key=lambda x: x.get("points", 0))
        
        message = self._create_envelope(
            "LEAGUE_COMPLETED",
            conversation_id="conv-league-complete",
            total_rounds=len(self.state.schedule),
            total_matches=sum(len(r) for r in self.state.schedule),
            champion={
                "player_id": champion.get("player_id") if champion else None,
                "display_name": champion.get("display_name") if champion else None,
                "points": champion.get("points", 0) if champion else 0
            } if champion else None,
            final_standings=[
                {
                    "rank": entry.get("rank"),
                    "player_id": entry.get("player_id"),
                    "display_name": entry.get("display_name"),
                    "points": entry.get("points", 0)
                }
                for entry in standings_list
            ]
        )
        
        # Send to all players using notify_league_completed method
        await self._broadcast_league_completed_to_players(message)
        
        # Also notify all referees
        for referee_id in self.state.registered_referees.keys():
            await self._notify_referee_league_completed(referee_id, message)
        
        self.state.logger.info("LEAGUE_COMPLETED_BROADCAST",
                               champion=champion.get("player_id") if champion else None,
                               total_rounds=len(self.state.schedule))
    
    async def _broadcast_league_completed_to_players(self, message: dict) -> list:
        """Broadcast LEAGUE_COMPLETED using notify_league_completed method."""
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for player_id, player_data in self.state.registered_players.items():
                if not player_data["active"]:
                    continue
                
                endpoint = player_data["endpoint"]
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "notify_league_completed",
                        "params": message,
                        "id": 2001
                    }
                    
                    response = await client.post(endpoint, json=payload)
                    results.append({
                        "player_id": player_id,
                        "status": "sent",
                        "status_code": response.status_code
                    })
                    
                    self.state.logger.debug("LEAGUE_COMPLETED_SENT",
                                            recipient=player_id)
                    
                except Exception as e:
                    results.append({
                        "player_id": player_id,
                        "status": "failed",
                        "error": str(e)
                    })
                    self.state.logger.warning("LEAGUE_COMPLETED_SEND_FAILED",
                                              recipient=player_id,
                                              error=str(e))
        
        return results
    
    async def _notify_referee_league_completed(self, referee_id: str, message: dict) -> bool:
        """Send LEAGUE_COMPLETED to a specific referee."""
        if referee_id not in self.state.registered_referees:
            return False
        
        referee_data = self.state.registered_referees[referee_id]
        endpoint = referee_data["endpoint"]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "notify_league_completed",
                    "params": message,
                    "id": 2001
                }
                await client.post(endpoint, json=payload)
                return True
            except Exception as e:
                self.state.logger.warning("REFEREE_LEAGUE_COMPLETED_FAILED",
                                          referee_id=referee_id,
                                          error=str(e))
                return False

