#!/usr/bin/env python3
"""
League Startup Script - Launches the full MCP League system.

Based on Chapter 8.2 of the League Protocol specification.

Startup Order:
1. League Manager (Port 8000) - Must be first
2. Referees (Ports 8001-8002) - Register with League Manager
3. Players (Ports 8101-8104) - Register with League Manager

All agents use:
- Protocol: league.v2
- Envelope format with timestamp (UTC) and auth_token
- JSON-RPC 2.0 over HTTP
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import json

# Add SHARED to path
SCRIPT_DIR = Path(__file__).parent.resolve()
SHARED_PATH = SCRIPT_DIR / "SHARED"
AGENTS_PATH = SCRIPT_DIR / "agents"
sys.path.insert(0, str(SHARED_PATH))


class AgentProcess:
    """Represents a running agent process."""
    
    def __init__(self, name: str, port: int, process: subprocess.Popen, log_file: str):
        self.name = name
        self.port = port
        self.process = process
        self.log_file = log_file
        self.started_at = datetime.utcnow()
    
    def is_running(self) -> bool:
        return self.process.poll() is None
    
    def stop(self):
        if self.is_running():
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class LeagueRunner:
    """
    Manages the lifecycle of all league agents.
    
    Handles:
    - Starting agents in correct order
    - Health checking
    - Graceful shutdown
    - Log management
    """
    
    def __init__(self, log_dir: Path = None, verbose: bool = False):
        self.log_dir = log_dir or (SCRIPT_DIR / "logs" / "runner")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose
        
        self.agents: List[AgentProcess] = []
        self.running = False
        
        # Agent configurations
        self.league_manager_config = {
            "name": "LeagueManager",
            "port": 8000,
            "path": AGENTS_PATH / "league_manager",
            "script": "main.py"
        }
        
        self.referee_configs = [
            {"name": "Referee Alpha", "port": 8001, "path": AGENTS_PATH / "referee_REF01"},
            {"name": "Referee Beta", "port": 8002, "path": AGENTS_PATH / "referee_REF02"},
        ]
        
        self.player_configs = [
            {"name": "Agent Alpha", "port": 8101, "path": AGENTS_PATH / "player_P01", "strategy": "random"},
            {"name": "Agent Beta", "port": 8102, "path": AGENTS_PATH / "player_P02", "strategy": "history"},
            {"name": "Agent Gamma", "port": 8103, "path": AGENTS_PATH / "player_P03", "strategy": "adaptive"},
            {"name": "Agent Delta", "port": 8104, "path": AGENTS_PATH / "player_P04", "strategy": "random"},
        ]
    
    def log(self, message: str):
        """Print a log message with timestamp."""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def start_agent(self, name: str, port: int, path: Path, args: List[str] = None) -> Optional[AgentProcess]:
        """
        Start a single agent process.
        
        Args:
            name: Agent display name
            port: Port to run on
            path: Path to agent directory
            args: Additional command line arguments
        
        Returns:
            AgentProcess if successful, None otherwise
        """
        script = path / "main.py"
        if not script.exists():
            self.log(f"ERROR: Script not found: {script}")
            return None
        
        # Prepare log file
        log_file = self.log_dir / f"{name.replace(' ', '_').lower()}_{port}.log"
        
        # Build command
        cmd = [sys.executable, str(script)]
        if args:
            cmd.extend(args)
        
        # Start process
        try:
            with open(log_file, 'w') as log_handle:
                env = os.environ.copy()
                env['PYTHONPATH'] = str(SHARED_PATH) + os.pathsep + env.get('PYTHONPATH', '')
                
                process = subprocess.Popen(
                    cmd,
                    cwd=str(path),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    env=env
                )
            
            agent = AgentProcess(name, port, process, str(log_file))
            self.agents.append(agent)
            
            if self.verbose:
                self.log(f"Started {name} on port {port} (PID: {process.pid})")
            
            return agent
            
        except Exception as e:
            self.log(f"ERROR starting {name}: {e}")
            return None
    
    def wait_for_agent(self, port: int, timeout: float = 10.0) -> bool:
        """
        Wait for an agent to become available.
        
        Args:
            port: Port to check
            timeout: Maximum wait time in seconds
        
        Returns:
            True if agent is available, False if timeout
        """
        import socket
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(0.5)
        
        return False
    
    def start_all(self) -> bool:
        """
        Start all agents in the correct order.
        
        Order:
        1. League Manager (must be first)
        2. Referees (register with League Manager)
        3. Players (register with League Manager)
        
        Returns:
            True if all agents started successfully
        """
        self.running = True
        
        print()
        print("=" * 60)
        print("  MCP League System Startup")
        print("  Protocol: league.v2")
        print("=" * 60)
        print()
        
        # Step 1: Start League Manager
        self.log("Step 1: Starting League Manager...")
        lm = self.start_agent(
            self.league_manager_config["name"],
            self.league_manager_config["port"],
            self.league_manager_config["path"]
        )
        
        if not lm:
            self.log("FAILED to start League Manager")
            return False
        
        # Wait for League Manager to be ready
        if not self.wait_for_agent(8000, timeout=15):
            self.log("League Manager did not become available")
            return False
        
        self.log("✓ League Manager ready on port 8000")
        time.sleep(1)  # Give it a moment to fully initialize
        
        # Step 2: Start Referees
        print()
        self.log("Step 2: Starting Referees...")
        
        for config in self.referee_configs:
            agent = self.start_agent(
                config["name"],
                config["port"],
                config["path"],
                ["--port", str(config["port"]), "--name", config["name"]]
            )
            
            if not agent:
                self.log(f"FAILED to start {config['name']}")
                return False
            
            if not self.wait_for_agent(config["port"], timeout=10):
                self.log(f"{config['name']} did not become available")
                return False
            
            self.log(f"✓ {config['name']} ready on port {config['port']}")
            time.sleep(0.5)
        
        # Step 3: Start Players
        print()
        self.log("Step 3: Starting Players...")
        
        for config in self.player_configs:
            agent = self.start_agent(
                config["name"],
                config["port"],
                config["path"],
                [
                    "--port", str(config["port"]),
                    "--name", config["name"],
                    "--strategy", config["strategy"]
                ]
            )
            
            if not agent:
                self.log(f"FAILED to start {config['name']}")
                return False
            
            if not self.wait_for_agent(config["port"], timeout=10):
                self.log(f"{config['name']} did not become available")
                return False
            
            self.log(f"✓ {config['name']} ready on port {config['port']} (strategy: {config['strategy']})")
            time.sleep(0.5)
        
        print()
        self.log("=" * 50)
        self.log("All agents started successfully!")
        self.log("=" * 50)
        
        return True
    
    def print_status(self):
        """Print the status of all agents."""
        print()
        print("Agent Status:")
        print("-" * 60)
        print(f"{'Name':<20} {'Port':<8} {'Status':<12} {'PID':<10}")
        print("-" * 60)
        
        for agent in self.agents:
            status = "Running" if agent.is_running() else "Stopped"
            pid = agent.process.pid if agent.is_running() else "-"
            print(f"{agent.name:<20} {agent.port:<8} {status:<12} {pid:<10}")
        
        print("-" * 60)
        print()
    
    def print_endpoints(self):
        """Print endpoint information for testing."""
        print()
        print("Endpoints:")
        print("-" * 60)
        print("League Manager:  http://localhost:8000/mcp")
        print("                 http://localhost:8000/health")
        print("                 http://localhost:8000/standings")
        print()
        print("Referees:")
        for config in self.referee_configs:
            print(f"  {config['name']}: http://localhost:{config['port']}/mcp")
        print()
        print("Players:")
        for config in self.player_configs:
            print(f"  {config['name']}: http://localhost:{config['port']}/mcp")
        print("-" * 60)
        print()
    
    def stop_all(self):
        """Stop all agents gracefully."""
        if not self.agents:
            return
        
        self.log("Stopping all agents...")
        
        # Stop in reverse order (players first, then referees, then league manager)
        for agent in reversed(self.agents):
            if agent.is_running():
                agent.stop()
                self.log(f"Stopped {agent.name}")
        
        self.agents.clear()
        self.running = False
        self.log("All agents stopped")
    
    def run_interactive(self):
        """Run in interactive mode with commands."""
        print()
        print("Interactive Mode - Available Commands:")
        print("  status  - Show agent status")
        print("  start   - Start the league (begin matches)")
        print("  round   - Announce next round")
        print("  stop    - Stop all agents and exit")
        print("  help    - Show this help")
        print()
        
        import httpx
        
        while self.running:
            try:
                cmd = input("league> ").strip().lower()
                
                if cmd == "status":
                    self.print_status()
                
                elif cmd == "start":
                    self.log("Starting league...")
                    try:
                        response = httpx.post(
                            "http://localhost:8000/mcp",
                            json={
                                "jsonrpc": "2.0",
                                "method": "start_league",
                                "params": {},
                                "id": 1
                            },
                            timeout=10.0
                        )
                        result = response.json()
                        if "result" in result:
                            schedule = result["result"].get("schedule_preview", [])
                            self.log(f"League started with {len(schedule)} rounds")
                            for round_info in schedule:
                                print(f"  Round {round_info['round_id']}:")
                                for match in round_info.get('matches', []):
                                    print(f"    {match['match_id']}: {match['player_A_id']} vs {match['player_B_id']}")
                        else:
                            self.log(f"Error: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        self.log(f"Error starting league: {e}")
                
                elif cmd == "round":
                    self.log("Announcing next round...")
                    try:
                        response = httpx.post(
                            "http://localhost:8000/mcp",
                            json={
                                "jsonrpc": "2.0",
                                "method": "announce_round",
                                "params": {},
                                "id": 2
                            },
                            timeout=30.0
                        )
                        result = response.json()
                        if "result" in result:
                            round_id = result["result"].get("round_id", "?")
                            matches = result["result"].get("matches", [])
                            self.log(f"Round {round_id} announced with {len(matches)} matches")
                            
                            # Wait a moment for matches to complete, then check standings
                            import time
                            time.sleep(1.5)  # Give matches time to complete
                            
                            # Check if league is complete by querying status
                            status_response = httpx.post(
                                "http://localhost:8000/mcp",
                                json={
                                    "jsonrpc": "2.0",
                                    "method": "league_query",
                                    "params": {"query_type": "GET_STATUS"},
                                    "id": 3
                                },
                                timeout=5.0
                            )
                            status_result = status_response.json()
                            if "result" in status_result:
                                league_status = status_result["result"]
                                current_round = league_status.get("current_round", 0)
                                total_rounds = league_status.get("total_rounds", 0)
                                
                                if current_round >= total_rounds and total_rounds > 0:
                                    print()
                                    print("=" * 60)
                                    print("🏆  LEAGUE COMPLETED!  🏆")
                                    print("=" * 60)
                                    # Get final standings
                                    standings_resp = httpx.get("http://localhost:8000/standings", timeout=5.0)
                                    standings = standings_resp.json()
                                    standings_list = standings.get("standings", [])
                                    if standings_list:
                                        champion = standings_list[0]
                                        print(f"\n🥇 CHAMPION: {champion.get('player_id')} - {champion.get('display_name', '')}")
                                        print(f"   Points: {champion.get('points', 0)}")
                                        print(f"   Record: W:{champion.get('wins', 0)} D:{champion.get('draws', 0)} L:{champion.get('losses', 0)}")
                                    print("\nFinal Standings:")
                                    print("-" * 50)
                                    for i, entry in enumerate(standings_list):
                                        medal = ["🥇", "🥈", "🥉", "  "][min(i, 3)]
                                        print(f"  {medal} #{entry.get('rank', '?')}: {entry.get('player_id', '?')} - "
                                              f"{entry.get('points', 0)} pts "
                                              f"(W:{entry.get('wins', 0)} D:{entry.get('draws', 0)} L:{entry.get('losses', 0)})")
                                    print("-" * 50)
                                    print("\nType 'stop' to exit or 'start' to begin a new league.")
                                    print()
                        else:
                            error_msg = result.get('error', {})
                            if isinstance(error_msg, dict):
                                msg = error_msg.get('message', 'Unknown error')
                            else:
                                msg = str(error_msg)
                            
                            if "No more rounds" in msg:
                                print()
                                print("=" * 60)
                                print("🏆  LEAGUE ALREADY COMPLETED!  🏆")
                                print("=" * 60)
                                # Show final standings
                                standings_resp = httpx.get("http://localhost:8000/standings", timeout=5.0)
                                standings = standings_resp.json()
                                standings_list = standings.get("standings", [])
                                if standings_list:
                                    champion = standings_list[0]
                                    print(f"\n🥇 CHAMPION: {champion.get('player_id')} - {champion.get('display_name', '')}")
                                print("\nType 'start' to begin a new league.")
                                print()
                            else:
                                self.log(f"Error: {msg}")
                    except Exception as e:
                        self.log(f"Error announcing round: {e}")
                
                elif cmd == "standings":
                    try:
                        response = httpx.get("http://localhost:8000/standings", timeout=5.0)
                        standings = response.json()
                        print()
                        print("Current Standings:")
                        print("-" * 50)
                        for entry in standings.get("standings", []):
                            print(f"  #{entry.get('rank', '?')}: {entry.get('player_id', '?')} - "
                                  f"{entry.get('points', 0)} pts "
                                  f"(W:{entry.get('wins', 0)} D:{entry.get('draws', 0)} L:{entry.get('losses', 0)})")
                        print("-" * 50)
                        print()
                    except Exception as e:
                        self.log(f"Error getting standings: {e}")
                
                elif cmd == "endpoints":
                    self.print_endpoints()
                
                elif cmd == "stop" or cmd == "quit" or cmd == "exit":
                    break
                
                elif cmd == "help":
                    print()
                    print("Commands:")
                    print("  status    - Show agent status")
                    print("  start     - Start the league (create schedule)")
                    print("  round     - Announce next round (run matches)")
                    print("  standings - Show current standings")
                    print("  endpoints - Show endpoint URLs")
                    print("  stop      - Stop all agents and exit")
                    print()
                
                elif cmd:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            
            except KeyboardInterrupt:
                print()
                break
            except EOFError:
                break


def main():
    parser = argparse.ArgumentParser(
        description="MCP League System Startup Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_league.py                  # Start all agents
  python run_league.py --interactive    # Start with interactive commands
  python run_league.py --verbose        # Verbose output
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode with commands"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait after starting (exit immediately)"
    )
    
    args = parser.parse_args()
    
    runner = LeagueRunner(verbose=args.verbose)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n")
        runner.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start all agents
        if not runner.start_all():
            runner.stop_all()
            sys.exit(1)
        
        # Show status and endpoints
        runner.print_status()
        runner.print_endpoints()
        
        if args.no_wait:
            print("Agents started. Use Ctrl+C to stop.")
            return
        
        if args.interactive:
            runner.run_interactive()
        else:
            print("Press Ctrl+C to stop all agents...")
            print()
            
            # Keep running
            while True:
                time.sleep(1)
                
                # Check if any agent died
                for agent in runner.agents:
                    if not agent.is_running():
                        runner.log(f"WARNING: {agent.name} has stopped unexpectedly")
    
    except KeyboardInterrupt:
        print("\n")
    
    finally:
        runner.stop_all()


if __name__ == "__main__":
    main()

