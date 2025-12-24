"""
Player Agent - MCP Server for game participation.

This agent participates in league matches:
- Registers with League Manager on startup
- Responds to game invitations
- Makes parity choices using configurable strategy
- Tracks match history for strategy improvement

Based on Chapters 3, 4, and 5 of the League Protocol specification.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Add SHARED to path for league_sdk
SHARED_PATH = Path(__file__).parent.parent.parent / "SHARED"
sys.path.insert(0, str(SHARED_PATH))

from league_sdk import (
    ConfigLoader, PlayerHistoryRepository, JsonLogger,
    MCPDiscovery, get_player_tools, get_player_resources
)
from handlers import PlayerHandlers
from strategy import RandomStrategy, HistoryBasedStrategy, StrategyManager
from resilience import RetryClient


class PlayerState:
    """Global state for the player agent."""
    
    def __init__(self, display_name: str, port: int, strategy_type: str = "random"):
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.load_system()
        self.league_id = self.system_config.default_league_id
        self.league_config = self.config_loader.load_league(self.league_id)
        
        # Player identity (assigned after registration)
        self.player_id: str = None
        self.auth_token: str = None
        self.display_name = display_name
        self.port = port
        self.endpoint = f"http://localhost:{port}/mcp"
        
        # League Manager endpoint
        lm_port = self.system_config.network.default_league_manager_port
        self.league_manager_endpoint = f"http://localhost:{lm_port}/mcp"
        
        # Logger (will be updated after registration)
        self.logger = JsonLogger(f"player_{display_name}", self.league_id)
        
        # History repository (will be initialized after registration)
        self.history_repo: PlayerHistoryRepository = None
        
        # Strategy
        self.strategy_type = strategy_type
        self.strategy_manager: StrategyManager = None
        
        # Registration status
        self.registered = False
        
        # Active game state
        self.current_match: dict = None
        
        # Retry configuration from system config
        retry_config = self.system_config.retry_policy
        self.max_retries = retry_config.max_retries
        self.backoff_strategy = retry_config.backoff_strategy

        # MCP Discovery (initialized after registration when player_id is known)
        self.mcp_discovery = None

    def init_mcp_discovery(self):
        """Initialize MCP tools and resources after registration."""
        player_id = self.player_id or "UNREGISTERED"
        self.mcp_discovery = MCPDiscovery(player_id, "player")

        # Register tools
        for tool in get_player_tools():
            self.mcp_discovery.register_tool(tool)

        # Register resources with handlers
        for resource in get_player_resources(player_id):
            handler = None
            if "stats" in resource.uri:
                handler = lambda: self.history_repo.get_stats() if self.history_repo else {}
            elif "history" in resource.uri:
                handler = lambda: {"matches": self.history_repo.get_matches(10) if self.history_repo else []}
            elif "config" in resource.uri:
                handler = lambda: {
                    "player_id": self.player_id,
                    "display_name": self.display_name,
                    "endpoint": self.endpoint,
                    "strategy": self.strategy_type,
                    "registered": self.registered
                }
            self.mcp_discovery.register_resource(resource, handler)


# Global state (initialized in main)
state: PlayerState = None


async def register_with_league_manager():
    """
    Register with the League Manager on startup.
    
    Sends LEAGUE_REGISTER_REQUEST and waits for response.
    Uses retry logic with exponential backoff.
    """
    global state
    
    state.logger.info("REGISTRATION_STARTING",
                      league_manager=state.league_manager_endpoint)
    
    conversation_id = f"conv-player-{state.display_name.lower().replace(' ', '-')}-reg-001"
    request_payload = {
        "jsonrpc": "2.0",
        "method": "register_player",
        "params": {
            "protocol": "league.v2",
            "message_type": "LEAGUE_REGISTER_REQUEST",
            "sender": f"player:{state.display_name.lower().replace(' ', '_')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversation_id": conversation_id,
            "player_meta": {
                "display_name": state.display_name,
                "version": "1.0.0",
                "game_types": ["even_odd"],
                "contact_endpoint": state.endpoint
            }
        },
        "id": 1
    }
    
    # Use retry client for registration
    retry_client = RetryClient(
        max_retries=state.max_retries,
        backoff_strategy=state.backoff_strategy,
        logger=state.logger
    )
    
    try:
        response = await retry_client.post(
            state.league_manager_endpoint,
            json=request_payload
        )
        
        if response and response.status_code == 200:
            result = response.json().get("result", {})
            
            if result.get("status") == "ACCEPTED":
                state.player_id = result.get("player_id")
                state.auth_token = result.get("auth_token")
                state.registered = True

                # Update logger with actual player_id
                state.logger = JsonLogger(
                    f"player:{state.player_id}",
                    state.league_id
                )

                # Initialize history repository
                state.history_repo = PlayerHistoryRepository(state.player_id)

                # Initialize strategy manager
                state.strategy_manager = StrategyManager(
                    state.strategy_type,
                    state.history_repo
                )

                # Initialize MCP discovery with actual player_id
                state.init_mcp_discovery()
                
                state.logger.info("REGISTRATION_SUCCESS",
                                  player_id=state.player_id)
                print(f"✓ Registered as {state.player_id}")
                return True
            else:
                reason = result.get("reason", "Unknown")
                state.logger.error("REGISTRATION_REJECTED", reason=reason)
                print(f"✗ Registration rejected: {reason}")
                return False
        else:
            status = response.status_code if response else "No response"
            state.logger.error("REGISTRATION_FAILED", status=status)
            print(f"✗ Registration failed: {status}")
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
    
    state.logger.info("PLAYER_STARTED", port=state.port)
    yield
    state.logger.info("PLAYER_STOPPED")


# Create FastAPI app
app = FastAPI(
    title="Player Agent MCP Server",
    description="Game participant for the MCP League Protocol",
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
handlers: PlayerHandlers = None


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP endpoint handling JSON-RPC 2.0 requests.
    
    Supported methods:
    - game_invitation: Handle game invitation from referee
    - choose_parity: Make a parity choice
    - notify_game_over: Receive game result
    - notify: General notifications
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
        # MCP Discovery methods (tools/list, resources/list, resources/read)
        if state.mcp_discovery:
            discovery_result = state.mcp_discovery.handle_mcp_method(method, params)
            if discovery_result is not None:
                return JSONResponse(create_jsonrpc_response(discovery_result, request_id))

        # Standard player methods
        if method == "handle_game_invitation" or method == "game_invitation":
            # GAME_INVITATION (Ch. 8.7.1)
            result = await handlers.handle_game_invitation(params)
        elif method == "choose_parity":
            # CHOOSE_PARITY_CALL (Ch. 8.7.3)
            result = await handlers.handle_choose_parity(params)
        elif method == "notify_match_result" or method == "notify_game_over":
            # GAME_OVER (Ch. 8.7.5)
            result = await handlers.handle_game_over(params)
        elif method == "notify" or method == "notify_round":
            # ROUND_ANNOUNCEMENT and general notifications (Ch. 8.6)
            result = await handlers.handle_notification(params)
        elif method == "notify_league_completed":
            # LEAGUE_COMPLETED (Ch. 8.9)
            result = await handlers.handle_league_completed(params)
        elif method == "notify_round_completed":
            # ROUND_COMPLETED (Ch. 8.8)
            result = await handlers.handle_round_completed(params)
        elif method == "update_standings":
            # LEAGUE_STANDINGS_UPDATE (Ch. 8.8)
            result = await handlers.handle_standings_update(params)
        elif method == "get_stats":
            result = await handlers.get_stats()
        elif method == "get_history":
            result = await handlers.get_history(params)
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
    stats = state.history_repo.get_stats() if state.history_repo else {}
    return {
        "status": "healthy",
        "player_id": state.player_id,
        "registered": state.registered,
        "strategy": state.strategy_type,
        "stats": stats
    }


def main():
    global state, handlers
    
    parser = argparse.ArgumentParser(description="Player Agent")
    parser.add_argument("--port", type=int, default=8101,
                        help="Port to run on (default: 8101)")
    parser.add_argument("--name", type=str, default="Agent Alpha",
                        help="Display name for this player")
    parser.add_argument("--strategy", type=str, default="random",
                        choices=["random", "history", "adaptive"],
                        help="Strategy to use (default: random)")
    args = parser.parse_args()
    
    # Initialize state
    state = PlayerState(args.name, args.port, args.strategy)
    
    # Initialize handlers
    handlers = PlayerHandlers(state)
    
    print(f"Starting Player Agent on port {args.port}...")
    print(f"Display Name: {args.name}")
    print(f"Strategy: {args.strategy}")
    print(f"League: {state.league_id}")
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()

