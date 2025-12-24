"""
Referee Agent - MCP Server for match management.

This agent handles individual matches:
- Registers with League Manager on startup
- Receives match assignments via ROUND_ANNOUNCEMENT
- Manages game flow (invitations, moves, results)
- Reports results back to League Manager

Based on Chapters 3, 4, and 8 of the League Protocol specification.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Add SHARED to path for league_sdk
SHARED_PATH = Path(__file__).parent.parent.parent / "SHARED"
sys.path.insert(0, str(SHARED_PATH))

from league_sdk import ConfigLoader, MatchRepository, JsonLogger
from game_logic import EvenOddGame
from handlers import RefereeHandlers


class RefereeState:
    """Global state for the referee agent."""

    def __init__(self, referee_display_name: str, port: int):
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.load_system()
        self.league_id = self.system_config.default_league_id
        self.league_config = self.config_loader.load_league(self.league_id)

        # Referee identity (assigned after registration)
        self.referee_id: str = None
        self.auth_token: str = None
        self.display_name = referee_display_name
        self.port = port
        self.endpoint = f"http://localhost:{port}/mcp"

        # League Manager endpoint
        lm_port = self.system_config.network.default_league_manager_port
        self.league_manager_endpoint = f"http://localhost:{lm_port}/mcp"

        # Logger (will be updated after registration)
        self.logger = JsonLogger(f"referee_{referee_display_name}", self.league_id)

        # Mutex locks for critical sections (async-safe)
        self._matches_lock = asyncio.Lock()  # Protects active_matches dictionary
        self._endpoints_lock = asyncio.Lock()  # Protects player_endpoints dictionary

        # Active matches
        self.active_matches: dict = {}  # match_id -> match state

        # Player endpoints (received from round announcements)
        self.player_endpoints: dict = {}  # player_id -> endpoint

        # Match repository
        self.match_repo = MatchRepository(self.league_id)

        # Game logic
        self.game = EvenOddGame()

        # Registration status
        self.registered = False


# Global state (initialized in main)
state: RefereeState = None


async def register_with_league_manager():
    """
    Register with the League Manager on startup.
    
    Sends REFEREE_REGISTER_REQUEST and waits for response.
    """
    global state
    
    state.logger.info("REGISTRATION_STARTING", 
                      league_manager=state.league_manager_endpoint)
    
    conversation_id = f"conv-ref-{state.display_name.lower().replace(' ', '-')}-reg-001"
    request_payload = {
        "jsonrpc": "2.0",
        "method": "register_referee",
        "params": {
            "protocol": "league.v2",
            "message_type": "REFEREE_REGISTER_REQUEST",
            "sender": f"referee:{state.display_name.lower().replace(' ', '_')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversation_id": conversation_id,
            "referee_meta": {
                "display_name": state.display_name,
                "version": "1.0.0",
                "game_types": ["even_odd"],
                "contact_endpoint": state.endpoint,
                "max_concurrent_matches": 2
            }
        },
        "id": 1
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                state.league_manager_endpoint,
                json=request_payload
            )
            
            if response.status_code == 200:
                result = response.json().get("result", {})
                
                if result.get("status") == "ACCEPTED":
                    state.referee_id = result.get("referee_id")
                    state.auth_token = result.get("auth_token")
                    state.registered = True
                    
                    # Update logger with actual referee_id
                    state.logger = JsonLogger(
                        f"referee:{state.referee_id}", 
                        state.league_id
                    )
                    
                    state.logger.info("REGISTRATION_SUCCESS",
                                      referee_id=state.referee_id)
                    print(f"✓ Registered as {state.referee_id}")
                    return True
                else:
                    reason = result.get("reason", "Unknown")
                    state.logger.error("REGISTRATION_REJECTED", reason=reason)
                    print(f"✗ Registration rejected: {reason}")
                    return False
            else:
                state.logger.error("REGISTRATION_FAILED",
                                   status_code=response.status_code)
                print(f"✗ Registration failed: HTTP {response.status_code}")
                return False
                
        except httpx.ConnectError:
            state.logger.error("REGISTRATION_FAILED",
                               error="Could not connect to League Manager")
            print(f"✗ Could not connect to League Manager at {state.league_manager_endpoint}")
            print("  Make sure the League Manager is running first!")
            return False
        except Exception as e:
            state.logger.error("REGISTRATION_FAILED", error=str(e))
            print(f"✗ Registration error: {e}")
            return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for startup/shutdown."""
    global state
    
    # Try to register on startup
    success = await register_with_league_manager()
    if not success:
        print("Warning: Running without registration. Some features may not work.")
    
    state.logger.info("REFEREE_STARTED", port=state.port)
    yield
    state.logger.info("REFEREE_STOPPED")


# Create FastAPI app
app = FastAPI(
    title="Referee Agent MCP Server",
    description="Match management for the MCP League Protocol",
    version="1.0.0",
    lifespan=lifespan
)


def create_jsonrpc_response(result: dict, request_id: int) -> dict:
    """Create a JSON-RPC 2.0 response."""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id
    }


def create_jsonrpc_error(code: int, message: str, request_id: int) -> dict:
    """Create a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": request_id
    }


# Initialize handlers (after state is created)
handlers: RefereeHandlers = None


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP endpoint handling JSON-RPC 2.0 requests.
    
    Supported methods:
    - notify: Receive notifications (ROUND_ANNOUNCEMENT, etc.)
    - run_match: Start and run a match
    - get_match_state: Query match state
    """
    global handlers
    
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            create_jsonrpc_error(-32700, "Parse error", None),
            status_code=400
        )
    
    if body.get("jsonrpc") != "2.0":
        return JSONResponse(
            create_jsonrpc_error(-32600, "Invalid Request", body.get("id")),
            status_code=400
        )
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    state.logger.debug("REQUEST_RECEIVED", method=method)
    
    try:
        if method == "notify" or method == "notify_round":
            # Handle notifications (ROUND_ANNOUNCEMENT, etc.)
            result = await handlers.handle_notification(params)
        elif method == "notify_league_completed":
            # Handle league completed notification
            result = await handlers.handle_league_completed(params)
        elif method == "notify_round_completed":
            # Handle round completed notification
            result = await handlers.handle_round_completed(params)
        elif method == "run_match":
            # Manually trigger a match
            result = await handlers.run_match(params)
        elif method == "get_match_state":
            result = await handlers.get_match_state(params)
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
        "referee_id": state.referee_id,
        "registered": state.registered,
        "active_matches": len(state.active_matches)
    }


def main():
    global state, handlers
    
    parser = argparse.ArgumentParser(description="Referee Agent")
    parser.add_argument("--port", type=int, default=8001, 
                        help="Port to run on (default: 8001)")
    parser.add_argument("--name", type=str, default="Referee Alpha",
                        help="Display name for this referee")
    args = parser.parse_args()
    
    # Initialize state
    state = RefereeState(args.name, args.port)
    
    # Initialize handlers
    handlers = RefereeHandlers(state)
    
    print(f"Starting Referee Agent on port {args.port}...")
    print(f"Display Name: {args.name}")
    print(f"League: {state.league_id}")
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()

