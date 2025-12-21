"""
Unit tests for resilience.py (Retry and Circuit Breaker)
"""

import sys
from pathlib import Path

# Add agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "player_P01"))

import unittest
import asyncio
from datetime import datetime, timedelta
from resilience import (
    ErrorCode,
    RetryableError,
    RetryClient,
    CircuitBreaker,
    ResilientClient,
)


class TestErrorCode(unittest.TestCase):
    """Tests for ErrorCode enum."""
    
    def test_timeout_error(self):
        """Test timeout error code."""
        self.assertEqual(ErrorCode.TIMEOUT_ERROR.value, "E001")
    
    def test_connection_error(self):
        """Test connection error code."""
        self.assertEqual(ErrorCode.CONNECTION_ERROR.value, "E009")
    
    def test_all_codes_exist(self):
        """Test all error codes exist."""
        codes = [
            ErrorCode.TIMEOUT_ERROR,
            ErrorCode.MISSING_REQUIRED_FIELD,
            ErrorCode.INVALID_PARITY_CHOICE,
            ErrorCode.PLAYER_NOT_REGISTERED,
            ErrorCode.CONNECTION_ERROR,
            ErrorCode.AUTH_TOKEN_MISSING,
            ErrorCode.AUTH_TOKEN_INVALID,
        ]
        
        for code in codes:
            self.assertIsNotNone(code.value)


class TestRetryableError(unittest.TestCase):
    """Tests for RetryableError exception."""
    
    def test_create_error(self):
        """Test creating a retryable error."""
        error = RetryableError(
            ErrorCode.TIMEOUT_ERROR,
            "Request timed out",
            retry_count=1
        )
        
        self.assertEqual(error.error_code, ErrorCode.TIMEOUT_ERROR)
        self.assertEqual(error.message, "Request timed out")
        self.assertEqual(error.retry_count, 1)
    
    def test_error_string(self):
        """Test error string representation."""
        error = RetryableError(
            ErrorCode.CONNECTION_ERROR,
            "Connection failed"
        )
        
        self.assertIn("E009", str(error))
        self.assertIn("Connection failed", str(error))


class TestRetryClient(unittest.TestCase):
    """Tests for RetryClient class."""
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        client = RetryClient(
            max_retries=3,
            backoff_strategy="exponential",
            initial_delay=1.0,
            max_delay=30.0
        )
        
        # Attempt 0: ~1s
        delay0 = client._calculate_delay(0)
        self.assertGreater(delay0, 0.5)
        self.assertLess(delay0, 1.5)
        
        # Attempt 1: ~2s
        delay1 = client._calculate_delay(1)
        self.assertGreater(delay1, 1.5)
        self.assertLess(delay1, 2.5)
        
        # Attempt 2: ~4s
        delay2 = client._calculate_delay(2)
        self.assertGreater(delay2, 3.0)
        self.assertLess(delay2, 5.0)
    
    def test_calculate_delay_linear(self):
        """Test linear backoff delay calculation."""
        client = RetryClient(
            max_retries=3,
            backoff_strategy="linear",
            initial_delay=2.0
        )
        
        # Attempt 0: ~2s
        delay0 = client._calculate_delay(0)
        self.assertGreater(delay0, 1.5)
        self.assertLess(delay0, 2.5)
        
        # Attempt 1: ~4s
        delay1 = client._calculate_delay(1)
        self.assertGreater(delay1, 3.0)
        self.assertLess(delay1, 5.0)
    
    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        client = RetryClient(
            max_retries=10,
            backoff_strategy="exponential",
            initial_delay=1.0,
            max_delay=10.0
        )
        
        # Very high attempt should be capped
        delay = client._calculate_delay(10)
        self.assertLessEqual(delay, 10.0)
    
    def test_calculate_delay_jitter(self):
        """Test that jitter adds randomness."""
        client = RetryClient(initial_delay=1.0)
        
        # Same attempt should give slightly different delays due to jitter
        delays = [client._calculate_delay(0) for _ in range(10)]
        
        # Not all should be exactly equal (jitter adds variance)
        self.assertGreater(len(set(round(d, 2) for d in delays)), 1)


class TestCircuitBreaker(unittest.TestCase):
    """Tests for CircuitBreaker class."""
    
    def test_initial_state_closed(self):
        """Test that circuit starts closed."""
        cb = CircuitBreaker(failure_threshold=3)
        
        self.assertEqual(cb.state, CircuitBreaker.State.CLOSED)
        self.assertTrue(cb.can_execute())
    
    def test_opens_after_threshold(self):
        """Test that circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreaker.State.CLOSED)
        
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreaker.State.CLOSED)
        
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreaker.State.OPEN)
        self.assertFalse(cb.can_execute())
    
    def test_success_resets_failures(self):
        """Test that success resets failure count."""
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.failure_count, 2)
        
        cb.record_success()
        self.assertEqual(cb.failure_count, 0)
        self.assertEqual(cb.state, CircuitBreaker.State.CLOSED)
    
    def test_half_open_after_recovery_timeout(self):
        """Test transition to half-open after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreaker.State.OPEN)
        
        # Wait for recovery timeout
        import time
        time.sleep(0.15)
        
        # Should transition to half-open
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.state, CircuitBreaker.State.HALF_OPEN)
    
    def test_half_open_success_closes(self):
        """Test that success in half-open closes circuit."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        
        cb.record_failure()
        cb.record_failure()
        
        import time
        time.sleep(0.02)
        cb.can_execute()  # Triggers transition to half-open
        
        cb.record_success()
        self.assertEqual(cb.state, CircuitBreaker.State.CLOSED)
    
    def test_half_open_failure_opens(self):
        """Test that failure in half-open opens circuit."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        
        cb.record_failure()
        cb.record_failure()
        
        import time
        time.sleep(0.02)
        cb.can_execute()  # Triggers transition to half-open
        
        cb.record_failure()
        self.assertEqual(cb.state, CircuitBreaker.State.OPEN)


class TestCircuitBreakerStates(unittest.TestCase):
    """Tests for CircuitBreaker state enum."""
    
    def test_state_values(self):
        """Test state values."""
        self.assertEqual(CircuitBreaker.State.CLOSED.value, "CLOSED")
        self.assertEqual(CircuitBreaker.State.OPEN.value, "OPEN")
        self.assertEqual(CircuitBreaker.State.HALF_OPEN.value, "HALF_OPEN")


class TestResilientClientIntegration(unittest.TestCase):
    """Integration tests for ResilientClient."""
    
    def test_client_creation(self):
        """Test creating a resilient client."""
        client = ResilientClient(
            max_retries=3,
            backoff_strategy="exponential",
            failure_threshold=5,
            recovery_timeout=30.0
        )
        
        self.assertIsInstance(client.retry_client, RetryClient)
        self.assertIsInstance(client.circuit_breaker, CircuitBreaker)


if __name__ == "__main__":
    unittest.main()

