"""
League Manager Agent - MCP Server using FastAPI.

This is the central orchestrator for the league system.
Handles:
- Referee and player registration
- Match scheduling (Round-Robin)
- Round announcements
- Standings management

Based on Chapters 4, 8, and the league protocol specification.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Add SHARED to path for league_sdk
SHARED_PATH = Path(__file__).parent.parent.parent / "SHARED"
sys.path.insert(0, str(SHARED_PATH))

from league_sdk import ConfigLoader, StandingsRepository, JsonLogger
from handlers import LeagueHandlers
from scheduler import RoundRobinScheduler


# Global state
class LeagueState:
    """Global state for the league manager."""

    def __init__(self):
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.load_system()
        self.league_id = self.system_config.default_league_id
        self.league_config = self.config_loader.load_league(self.league_id)

        # Logger
        self.logger = JsonLogger("league_manager", self.league_id)

        # Mutex locks for critical sections (async-safe)
        self._registration_lock = asyncio.Lock()  # Protects referee/player registration
        self._round_lock = asyncio.Lock()  # Protects round state changes
        self._match_result_lock = asyncio.Lock()  # Protects match result processing

        # Registered agents (runtime state)
        self.registered_referees: dict = {}  # referee_id -> {endpoint, auth_token, ...}
        self.registered_players: dict = {}   # player_id -> {endpoint, auth_token, ...}

        # Counters for ID assignment
        self._referee_counter = 0
        self._player_counter = 0

        # Match schedule
        self.schedule: list = []
        self.current_round = 0
        self.matches_completed_this_round = 0

        # Scheduler
        self.scheduler = RoundRobinScheduler()

        # Standings repository
        self.standings_repo = StandingsRepository(self.league_id)


# Create global state instance
state = LeagueState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for startup/shutdown."""
    state.logger.info("LEAGUE_MANAGER_STARTED", 
                      league_id=state.league_id,
                      port=state.system_config.network.default_league_manager_port)
    yield
    state.logger.info("LEAGUE_MANAGER_STOPPED", league_id=state.league_id)


# Create FastAPI app
app = FastAPI(
    title="League Manager MCP Server",
    description="Central orchestrator for the MCP League Protocol",
    version="1.0.0",
    lifespan=lifespan
)


def create_envelope(message_type: str, **extra_fields) -> dict:
    """Create a protocol envelope with required fields."""
    return {
        "protocol": "league.v2",
        "message_type": message_type,
        "sender": "league_manager",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **extra_fields
    }


def create_jsonrpc_response(result: dict, request_id: int) -> dict:
    """Create a JSON-RPC 2.0 response."""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }


def create_jsonrpc_error(code: int, message: str, request_id: int, data: dict = None) -> dict:
    """Create a JSON-RPC 2.0 error response."""
    error = {"code": code, "message": message}
    if data:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "error": error,
        "id": request_id
    }


# Initialize handlers
handlers = LeagueHandlers(state)


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP endpoint handling JSON-RPC 2.0 requests.
    
    Supported methods:
    - register_referee: Register a new referee
    - register_player: Register a new player  
    - report_match_result: Report match results from referee
    - league_query: Query league state (standings, etc.)
    - start_league: Start the league and create schedule
    - announce_round: Announce a new round
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            create_jsonrpc_error(-32700, "Parse error", None),
            status_code=400
        )
    
    # Validate JSON-RPC structure
    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            create_jsonrpc_error(-32600, "Invalid Request - must be JSON-RPC 2.0", body.get("id")),
            status_code=400
        )
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    state.logger.debug("REQUEST_RECEIVED", method=method, request_id=request_id)
    
    # Route to appropriate handler
    try:
        if method == "register_referee":
            result = await handlers.handle_register_referee(params)
        elif method == "register_player":
            result = await handlers.handle_register_player(params)
        elif method == "report_match_result":
            result = await handlers.handle_match_result_report(params)
        elif method == "league_query":
            result = await handlers.handle_league_query(params)
        elif method == "start_league":
            result = await handlers.handle_start_league(params)
        elif method == "announce_round":
            result = await handlers.handle_announce_round(params)
        else:
            return JSONResponse(
                create_jsonrpc_error(-32601, f"Method not found: {method}", request_id),
                status_code=400
            )
        
        return JSONResponse(create_jsonrpc_response(result, request_id))
    
    except ValueError as e:
        state.logger.warning("REQUEST_ERROR", method=method, error=str(e))
        return JSONResponse(
            create_jsonrpc_error(-32602, str(e), request_id),
            status_code=400
        )
    except Exception as e:
        state.logger.error("INTERNAL_ERROR", method=method, error=str(e))
        return JSONResponse(
            create_jsonrpc_error(-32603, f"Internal error: {str(e)}", request_id),
            status_code=500
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "league_id": state.league_id,
        "registered_players": len(state.registered_players),
        "registered_referees": len(state.registered_referees),
        "current_round": state.current_round
    }


@app.get("/standings")
async def get_standings():
    """Get current standings (convenience endpoint)."""
    return state.standings_repo.load()


if __name__ == "__main__":
    port = state.system_config.network.default_league_manager_port
    print(f"Starting League Manager on port {port}...")
    print(f"League: {state.league_id}")
    uvicorn.run(app, host="0.0.0.0", port=port)

