"""
Unit tests for message envelope format
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import json

import unittest


class TestEnvelopeFormat(unittest.TestCase):
    """Tests for MCP message envelope format."""
    
    def create_envelope(self, message_type, sender, **kwargs):
        """Create a message envelope."""
        envelope = {
            "protocol": "league.v2",
            "message_type": message_type,
            "sender": sender,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            **kwargs
        }
        return envelope
    
    def test_basic_envelope(self):
        """Test basic envelope structure."""
        envelope = self.create_envelope(
            "GAME_INVITATION",
            "referee:REF01"
        )
        
        self.assertEqual(envelope["protocol"], "league.v2")
        self.assertEqual(envelope["message_type"], "GAME_INVITATION")
        self.assertEqual(envelope["sender"], "referee:REF01")
        self.assertIn("timestamp", envelope)
    
    def test_timestamp_format(self):
        """Test timestamp is ISO 8601 with Z suffix."""
        envelope = self.create_envelope("TEST", "sender")
        timestamp = envelope["timestamp"]
        
        self.assertTrue(timestamp.endswith("Z"))
        
        # Should be parseable
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        self.assertIsNotNone(dt)
    
    def test_envelope_with_auth_token(self):
        """Test envelope with auth_token."""
        envelope = self.create_envelope(
            "GAME_INVITATION",
            "referee:REF01",
            auth_token="tok_abc123"
        )
        
        self.assertEqual(envelope["auth_token"], "tok_abc123")
    
    def test_envelope_with_conversation_id(self):
        """Test envelope with conversation_id."""
        envelope = self.create_envelope(
            "GAME_INVITATION",
            "referee:REF01",
            conversation_id="conv-r1m1-001"
        )
        
        self.assertEqual(envelope["conversation_id"], "conv-r1m1-001")
    
    def test_envelope_json_serializable(self):
        """Test that envelope is JSON serializable."""
        envelope = self.create_envelope(
            "GAME_INVITATION",
            "referee:REF01",
            auth_token="tok_abc123",
            conversation_id="conv-001",
            match_id="R1M1"
        )
        
        # Should not raise
        json_str = json.dumps(envelope)
        self.assertIsInstance(json_str, str)
        
        # Should be deserializable
        parsed = json.loads(json_str)
        self.assertEqual(parsed["message_type"], "GAME_INVITATION")
    
    def test_sender_format_referee(self):
        """Test referee sender format."""
        envelope = self.create_envelope("TEST", "referee:REF01")
        
        sender = envelope["sender"]
        agent_type, agent_id = sender.split(":")
        
        self.assertEqual(agent_type, "referee")
        self.assertEqual(agent_id, "REF01")
    
    def test_sender_format_player(self):
        """Test player sender format."""
        envelope = self.create_envelope("TEST", "player:P01")
        
        sender = envelope["sender"]
        agent_type, agent_id = sender.split(":")
        
        self.assertEqual(agent_type, "player")
        self.assertEqual(agent_id, "P01")
    
    def test_sender_format_league_manager(self):
        """Test league manager sender format."""
        envelope = self.create_envelope("TEST", "league_manager")
        
        self.assertEqual(envelope["sender"], "league_manager")


class TestJsonRpcFormat(unittest.TestCase):
    """Tests for JSON-RPC 2.0 message format."""
    
    def create_request(self, method, params, id=1):
        """Create a JSON-RPC request."""
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": id
        }
    
    def create_response(self, result, id=1):
        """Create a JSON-RPC success response."""
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": id
        }
    
    def create_error_response(self, code, message, id=1):
        """Create a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": id
        }
    
    def test_request_format(self):
        """Test JSON-RPC request format."""
        request = self.create_request(
            "register_player",
            {"player_meta": {"display_name": "Test"}}
        )
        
        self.assertEqual(request["jsonrpc"], "2.0")
        self.assertEqual(request["method"], "register_player")
        self.assertIn("params", request)
        self.assertIn("id", request)
    
    def test_response_format(self):
        """Test JSON-RPC success response format."""
        response = self.create_response(
            {"player_id": "P01", "auth_token": "tok_abc"}
        )
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("result", response)
        self.assertEqual(response["result"]["player_id"], "P01")
    
    def test_error_response_format(self):
        """Test JSON-RPC error response format."""
        response = self.create_error_response(
            -32600,
            "Invalid Request"
        )
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32600)
    
    def test_request_serializable(self):
        """Test that request is JSON serializable."""
        request = self.create_request(
            "choose_parity",
            {"player_id": "P01", "choice": "even"}
        )
        
        json_str = json.dumps(request)
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["method"], "choose_parity")
    
    def test_request_id_matching(self):
        """Test that response id matches request id."""
        request = self.create_request("test", {}, id=42)
        response = self.create_response({"data": "test"}, id=42)
        
        self.assertEqual(request["id"], response["id"])


class TestMessageTypes(unittest.TestCase):
    """Tests for message type constants."""
    
    MESSAGE_TYPES = [
        "REFEREE_REGISTER_REQUEST",
        "REFEREE_REGISTER_RESPONSE",
        "LEAGUE_REGISTER_REQUEST",
        "LEAGUE_REGISTER_RESPONSE",
        "ROUND_ANNOUNCEMENT",
        "ROUND_COMPLETED",
        "GAME_INVITATION",
        "GAME_JOIN_ACK",
        "CHOOSE_PARITY_CALL",
        "CHOOSE_PARITY_RESPONSE",
        "GAME_OVER",
        "MATCH_RESULT_REPORT",
        "LEAGUE_STANDINGS_UPDATE",
        "LEAGUE_COMPLETED",
        "LEAGUE_ERROR",
        "GAME_ERROR",
        "LEAGUE_QUERY",
    ]
    
    def test_message_types_uppercase(self):
        """Test that all message types are uppercase."""
        for msg_type in self.MESSAGE_TYPES:
            self.assertEqual(msg_type, msg_type.upper())
    
    def test_message_types_snake_case(self):
        """Test that all message types use snake_case."""
        for msg_type in self.MESSAGE_TYPES:
            # Should contain underscores, not spaces or hyphens
            self.assertNotIn(" ", msg_type)
            self.assertNotIn("-", msg_type)
    
    def test_registration_messages(self):
        """Test registration message types."""
        registration = [
            "REFEREE_REGISTER_REQUEST",
            "REFEREE_REGISTER_RESPONSE",
            "LEAGUE_REGISTER_REQUEST",
            "LEAGUE_REGISTER_RESPONSE",
        ]
        
        for msg in registration:
            self.assertIn("REGISTER", msg)
    
    def test_game_messages(self):
        """Test game message types."""
        game = [
            "GAME_INVITATION",
            "GAME_JOIN_ACK",
            "GAME_OVER",
            "GAME_ERROR",
        ]
        
        for msg in game:
            self.assertIn("GAME", msg)


if __name__ == "__main__":
    unittest.main()

