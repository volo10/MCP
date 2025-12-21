"""
Unit tests for logger.py (JSON Logger)
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add SHARED to path
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

import unittest
from league_sdk.logger import JsonLogger


class TestJsonLogger(unittest.TestCase):
    """Tests for JsonLogger class."""

    def setUp(self):
        """Set up test fixtures with temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.logger = JsonLogger("test_component", log_root=self.temp_dir)
    
    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_log_basic(self):
        """Test basic logging."""
        self.logger.log("test_event", level="INFO", data="test")

        # Read log file
        log_content = self._read_last_log()

        self.assertEqual(log_content["event_type"], "test_event")
        self.assertEqual(log_content["level"], "INFO")
        self.assertEqual(log_content["component"], "test_component")
        self.assertEqual(log_content["details"]["data"], "test")
    
    def test_log_timestamp_format(self):
        """Test that timestamp is ISO 8601 with Z suffix."""
        self.logger.log("test_event")
        
        log_content = self._read_last_log()
        timestamp = log_content["timestamp"]
        
        self.assertTrue(timestamp.endswith("Z"))
        # Should be parseable
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    
    def test_log_info(self):
        """Test info level logging."""
        self.logger.info("info_event", key="value")

        log_content = self._read_last_log()

        self.assertEqual(log_content["level"], "INFO")
        self.assertEqual(log_content["details"]["key"], "value")
    
    def test_log_debug(self):
        """Test debug level logging."""
        self.logger.debug("debug_event", detail="some detail")

        log_content = self._read_last_log()

        self.assertEqual(log_content["level"], "DEBUG")
        self.assertEqual(log_content["details"]["detail"], "some detail")
    
    def test_log_warning(self):
        """Test warning level logging."""
        self.logger.warning("warning_event", issue="minor issue")

        log_content = self._read_last_log()

        self.assertEqual(log_content["level"], "WARNING")
        self.assertEqual(log_content["details"]["issue"], "minor issue")
    
    def test_log_error(self):
        """Test error level logging."""
        self.logger.error("error_event", error_code="E001", message="timeout")

        log_content = self._read_last_log()

        self.assertEqual(log_content["level"], "ERROR")
        self.assertEqual(log_content["details"]["error_code"], "E001")
    
    def test_log_message_sent(self):
        """Test logging sent messages."""
        self.logger.log_message_sent(
            message_type="GAME_INVITATION",
            recipient="player:P01",
            conversation_id="conv-001",
            success=True
        )

        log_content = self._read_last_log()

        self.assertEqual(log_content["event_type"], "MESSAGE_SENT")
        self.assertEqual(log_content["details"]["message_type"], "GAME_INVITATION")
        self.assertEqual(log_content["details"]["recipient"], "player:P01")
        self.assertTrue(log_content["details"]["success"])
    
    def test_log_message_received(self):
        """Test logging received messages."""
        self.logger.log_message_received(
            message_type="GAME_JOIN_ACK",
            sender="player:P01",
            conversation_id="conv-001"
        )

        log_content = self._read_last_log()

        self.assertEqual(log_content["event_type"], "MESSAGE_RECEIVED")
        self.assertEqual(log_content["details"]["message_type"], "GAME_JOIN_ACK")
        self.assertEqual(log_content["details"]["sender"], "player:P01")
    
    def test_log_multiple_entries(self):
        """Test logging multiple entries."""
        self.logger.info("event_1")
        self.logger.info("event_2")
        self.logger.info("event_3")
        
        lines = self._read_all_logs()
        
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0]["event_type"], "event_1")
        self.assertEqual(lines[1]["event_type"], "event_2")
        self.assertEqual(lines[2]["event_type"], "event_3")
    
    def test_log_creates_directory(self):
        """Test that log creates directory if needed."""
        nested_dir = self.temp_dir / "nested" / "path"
        logger = JsonLogger("test", log_root=nested_dir)

        logger.info("test_event")

        self.assertTrue(nested_dir.exists())
    
    def test_log_with_dict_data(self):
        """Test logging with dict data."""
        self.logger.info("event", data={"key": "value", "nested": {"a": 1}})

        log_content = self._read_last_log()

        self.assertEqual(log_content["details"]["data"]["key"], "value")
        self.assertEqual(log_content["details"]["data"]["nested"]["a"], 1)
    
    def test_log_with_list_data(self):
        """Test logging with list data."""
        self.logger.info("event", items=[1, 2, 3])

        log_content = self._read_last_log()

        self.assertEqual(log_content["details"]["items"], [1, 2, 3])
    
    def test_log_file_extension(self):
        """Test that log file has .log.jsonl extension."""
        self.logger.info("test")
        
        log_files = list(self.temp_dir.rglob("*.log.jsonl"))
        self.assertGreater(len(log_files), 0)
    
    def test_log_component_subdirectory(self):
        """Test that logs are in component subdirectory."""
        logger = JsonLogger("referee:REF01", log_root=self.temp_dir)
        logger.info("test")

        log_files = list(self.temp_dir.rglob("*.log.jsonl"))
        self.assertGreater(len(log_files), 0)
    
    def _read_last_log(self):
        """Read the last log entry."""
        log_files = list(self.temp_dir.rglob("*.log.jsonl"))
        if not log_files:
            return None
        
        with open(log_files[0], "r") as f:
            lines = f.readlines()
            if lines:
                return json.loads(lines[-1])
        return None
    
    def _read_all_logs(self):
        """Read all log entries."""
        log_files = list(self.temp_dir.rglob("*.log.jsonl"))
        if not log_files:
            return []
        
        entries = []
        with open(log_files[0], "r") as f:
            for line in f:
                entries.append(json.loads(line.strip()))
        return entries


class TestJsonLoggerSubcategory(unittest.TestCase):
    """Tests for JsonLogger with subcategories."""
    
    def setUp(self):
        """Set up test fixtures with temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_different_components(self):
        """Test different components log to different files."""
        logger1 = JsonLogger("component_a", log_root=self.temp_dir)
        logger2 = JsonLogger("component_b", log_root=self.temp_dir)

        logger1.info("event_from_a")
        logger2.info("event_from_b")

        log_files = list(self.temp_dir.rglob("*.log.jsonl"))
        self.assertEqual(len(log_files), 2)


if __name__ == "__main__":
    unittest.main()

