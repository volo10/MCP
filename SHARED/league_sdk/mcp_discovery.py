"""
MCP Discovery Module - Tools and Resources listing.

Implements MCP-style discovery methods:
- tools/list: List available tools with schemas
- resources/list: List available resources
- resources/read: Read a specific resource

Based on Anthropic's Model Context Protocol specification.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ToolParameter:
    """Schema for a tool parameter."""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


@dataclass
class Tool:
    """MCP Tool definition."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)

    def to_schema(self) -> dict:
        """Convert to JSON Schema format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


@dataclass
class Resource:
    """MCP Resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_dict(self) -> dict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type
        }


class MCPDiscovery:
    """
    MCP Discovery handler for tools and resources.

    Usage:
        discovery = MCPDiscovery(agent_id="P01", agent_type="player")
        discovery.register_tool(Tool(...))
        discovery.register_resource(Resource(...))

        # In endpoint handler:
        if method == "tools/list":
            return discovery.handle_tools_list()
    """

    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._tools: List[Tool] = []
        self._resources: List[Resource] = []
        self._resource_handlers: Dict[str, Callable] = {}

    def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools.append(tool)

    def register_resource(self, resource: Resource, handler: Callable = None) -> None:
        """Register a resource with optional read handler."""
        self._resources.append(resource)
        if handler:
            self._resource_handlers[resource.uri] = handler

    def handle_tools_list(self) -> dict:
        """Handle tools/list method."""
        return {
            "tools": [tool.to_schema() for tool in self._tools]
        }

    def handle_resources_list(self) -> dict:
        """Handle resources/list method."""
        return {
            "resources": [res.to_dict() for res in self._resources]
        }

    def handle_resources_read(self, uri: str) -> dict:
        """Handle resources/read method."""
        handler = self._resource_handlers.get(uri)
        if handler:
            content = handler()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": content if isinstance(content, str) else str(content)
                    }
                ]
            }
        else:
            raise ValueError(f"Resource not found: {uri}")

    def handle_mcp_method(self, method: str, params: dict = None) -> Optional[dict]:
        """
        Handle MCP discovery methods.

        Returns None if method is not a discovery method.
        """
        if method == "tools/list":
            return self.handle_tools_list()
        elif method == "resources/list":
            return self.handle_resources_list()
        elif method == "resources/read":
            uri = params.get("uri") if params else None
            if not uri:
                raise ValueError("Missing required parameter: uri")
            return self.handle_resources_read(uri)
        return None


# =============================================================================
# Pre-defined tools for each agent type
# =============================================================================

def get_player_tools() -> List[Tool]:
    """Get standard tools for a Player agent."""
    return [
        Tool(
            name="handle_game_invitation",
            description="Receive and respond to a game invitation from a referee",
            parameters=[
                ToolParameter("match_id", "string", "Unique match identifier"),
                ToolParameter("round_id", "integer", "Current round number"),
                ToolParameter("opponent_id", "string", "Opponent's player ID"),
                ToolParameter("game_type", "string", "Type of game (e.g., even_odd)"),
            ]
        ),
        Tool(
            name="choose_parity",
            description="Make a parity choice (even or odd) for the current match",
            parameters=[
                ToolParameter("match_id", "string", "Unique match identifier"),
                ToolParameter("player_id", "string", "This player's ID"),
                ToolParameter("context", "object", "Game context information", required=False),
                ToolParameter("deadline", "string", "Response deadline (ISO timestamp)", required=False),
            ]
        ),
        Tool(
            name="notify_match_result",
            description="Receive notification of match result",
            parameters=[
                ToolParameter("match_id", "string", "Unique match identifier"),
                ToolParameter("game_result", "object", "Result details including winner and scores"),
            ]
        ),
    ]


def get_referee_tools() -> List[Tool]:
    """Get standard tools for a Referee agent."""
    return [
        Tool(
            name="notify",
            description="Receive notifications from League Manager (e.g., ROUND_ANNOUNCEMENT)",
            parameters=[
                ToolParameter("message_type", "string", "Type of notification message"),
                ToolParameter("round_id", "integer", "Round number", required=False),
                ToolParameter("matches", "array", "List of matches to referee", required=False),
            ]
        ),
        Tool(
            name="run_match",
            description="Manually trigger a match execution",
            parameters=[
                ToolParameter("match_id", "string", "Unique match identifier"),
                ToolParameter("player_a", "string", "First player's ID"),
                ToolParameter("player_b", "string", "Second player's ID"),
                ToolParameter("round_id", "integer", "Round number", required=False),
            ]
        ),
        Tool(
            name="get_match_state",
            description="Query the current state of a match",
            parameters=[
                ToolParameter("match_id", "string", "Unique match identifier"),
            ]
        ),
        Tool(
            name="notify_round_completed",
            description="Receive notification that a round has completed",
            parameters=[
                ToolParameter("round_id", "integer", "Completed round number"),
                ToolParameter("matches_completed", "integer", "Number of matches completed"),
            ]
        ),
        Tool(
            name="notify_league_completed",
            description="Receive notification that the league has completed",
            parameters=[
                ToolParameter("champion", "object", "Champion player details"),
                ToolParameter("final_standings", "array", "Final league standings"),
            ]
        ),
    ]


def get_league_manager_tools() -> List[Tool]:
    """Get standard tools for the League Manager agent."""
    return [
        Tool(
            name="register_referee",
            description="Register a referee agent with the league",
            parameters=[
                ToolParameter("referee_meta", "object", "Referee metadata including display_name, contact_endpoint, game_types"),
            ]
        ),
        Tool(
            name="register_player",
            description="Register a player agent with the league",
            parameters=[
                ToolParameter("player_meta", "object", "Player metadata including display_name, contact_endpoint, game_types"),
            ]
        ),
        Tool(
            name="start_league",
            description="Start the league and generate the match schedule",
            parameters=[]
        ),
        Tool(
            name="announce_round",
            description="Announce a new round and notify all participants",
            parameters=[
                ToolParameter("round_id", "integer", "Round number to announce", required=False),
            ]
        ),
        Tool(
            name="report_match_result",
            description="Receive match result report from a referee",
            parameters=[
                ToolParameter("match_id", "string", "Unique match identifier"),
                ToolParameter("round_id", "integer", "Round number"),
                ToolParameter("result", "object", "Match result including winner and scores"),
            ]
        ),
        Tool(
            name="query_league",
            description="Query league state (standings, schedule, players)",
            parameters=[
                ToolParameter("query_type", "string", "Type of query: GET_STANDINGS, GET_SCHEDULE, GET_PLAYERS"),
            ]
        ),
    ]


def get_player_resources(player_id: str) -> List[Resource]:
    """Get standard resources for a Player agent."""
    return [
        Resource(
            uri=f"player://{player_id}/stats",
            name="Player Statistics",
            description="Current player statistics (wins, losses, draws)"
        ),
        Resource(
            uri=f"player://{player_id}/history",
            name="Match History",
            description="List of past matches and results"
        ),
        Resource(
            uri=f"player://{player_id}/config",
            name="Player Configuration",
            description="Player agent configuration and strategy info"
        ),
    ]


def get_referee_resources(referee_id: str) -> List[Resource]:
    """Get standard resources for a Referee agent."""
    return [
        Resource(
            uri=f"referee://{referee_id}/active_matches",
            name="Active Matches",
            description="Currently active matches being refereed"
        ),
        Resource(
            uri=f"referee://{referee_id}/config",
            name="Referee Configuration",
            description="Referee agent configuration"
        ),
    ]


def get_league_manager_resources(league_id: str) -> List[Resource]:
    """Get standard resources for the League Manager agent."""
    return [
        Resource(
            uri=f"league://{league_id}/standings",
            name="League Standings",
            description="Current league standings table"
        ),
        Resource(
            uri=f"league://{league_id}/schedule",
            name="Match Schedule",
            description="Complete match schedule for all rounds"
        ),
        Resource(
            uri=f"league://{league_id}/players",
            name="Registered Players",
            description="List of registered players"
        ),
        Resource(
            uri=f"league://{league_id}/referees",
            name="Registered Referees",
            description="List of registered referees"
        ),
        Resource(
            uri=f"league://{league_id}/config",
            name="League Configuration",
            description="League configuration and rules"
        ),
    ]
