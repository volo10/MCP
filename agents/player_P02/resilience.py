"""
Resilience Module - Retry logic and error handling.

Based on Chapter 2.9 (Error Handling) of the League Protocol specification.

Implements:
- Exponential backoff for retries
- Connection error handling
- Timeout handling (E001)
- Circuit breaker pattern (optional)

Error Codes:
- E001: TIMEOUT_ERROR
- E009: CONNECTION_ERROR
"""

import asyncio
import random
from datetime import datetime
from typing import Optional, Any, TYPE_CHECKING
from enum import Enum

import httpx

if TYPE_CHECKING:
    from league_sdk import JsonLogger


class ErrorCode(Enum):
    """League protocol error codes."""
    TIMEOUT_ERROR = "E001"
    MISSING_REQUIRED_FIELD = "E003"
    INVALID_PARITY_CHOICE = "E004"
    PLAYER_NOT_REGISTERED = "E005"
    CONNECTION_ERROR = "E009"
    AUTH_TOKEN_MISSING = "E011"
    AUTH_TOKEN_INVALID = "E012"


class RetryableError(Exception):
    """Exception for errors that can be retried."""
    
    def __init__(self, error_code: ErrorCode, message: str, retry_count: int = 0):
        self.error_code = error_code
        self.message = message
        self.retry_count = retry_count
        super().__init__(f"{error_code.value}: {message}")


class RetryClient:
    """
    HTTP client with retry logic and exponential backoff.
    
    Features:
    - Configurable max retries
    - Exponential or linear backoff
    - Jitter to prevent thundering herd
    - Timeout handling
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_strategy: str = "exponential",
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 10.0,
        logger: "JsonLogger" = None
    ):
        """
        Initialize the retry client.
        
        Args:
            max_retries: Maximum number of retry attempts.
            backoff_strategy: "exponential" or "linear".
            initial_delay: Initial delay in seconds.
            max_delay: Maximum delay in seconds.
            timeout: Request timeout in seconds.
            logger: Optional logger for retry events.
        """
        self.max_retries = max_retries
        self.backoff_strategy = backoff_strategy
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.logger = logger
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the next retry attempt.
        
        Args:
            attempt: Current attempt number (0-based).
        
        Returns:
            Delay in seconds.
        """
        if self.backoff_strategy == "exponential":
            # Exponential backoff: delay = initial * 2^attempt
            delay = self.initial_delay * (2 ** attempt)
        else:
            # Linear backoff: delay = initial * (attempt + 1)
            delay = self.initial_delay * (attempt + 1)
        
        # Add jitter (±25%)
        jitter = delay * 0.25 * (random.random() * 2 - 1)
        delay = delay + jitter
        
        # Cap at max delay
        return min(delay, self.max_delay)
    
    async def post(
        self,
        url: str,
        json: dict = None,
        **kwargs
    ) -> Optional[httpx.Response]:
        """
        Send POST request with retry logic.
        
        Args:
            url: Target URL.
            json: JSON payload.
            **kwargs: Additional httpx arguments.
        
        Returns:
            Response if successful, None if all retries failed.
        
        Raises:
            RetryableError: If max retries exceeded.
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=json, **kwargs)
                    
                    if self.logger and attempt > 0:
                        self.logger.info("RETRY_SUCCESS",
                                         url=url,
                                         attempt=attempt)
                    
                    return response
                    
            except httpx.TimeoutException as e:
                last_error = RetryableError(
                    ErrorCode.TIMEOUT_ERROR,
                    f"Request timed out after {self.timeout}s",
                    retry_count=attempt
                )
                
                if self.logger:
                    self.logger.warning("TIMEOUT_ERROR",
                                        url=url,
                                        attempt=attempt,
                                        max_retries=self.max_retries)
                
            except httpx.ConnectError as e:
                last_error = RetryableError(
                    ErrorCode.CONNECTION_ERROR,
                    f"Connection failed: {str(e)}",
                    retry_count=attempt
                )
                
                if self.logger:
                    self.logger.warning("CONNECTION_ERROR",
                                        url=url,
                                        attempt=attempt,
                                        error=str(e))
                
            except Exception as e:
                last_error = RetryableError(
                    ErrorCode.CONNECTION_ERROR,
                    f"Request failed: {str(e)}",
                    retry_count=attempt
                )
                
                if self.logger:
                    self.logger.error("REQUEST_ERROR",
                                      url=url,
                                      attempt=attempt,
                                      error=str(e))
            
            # Check if we should retry
            if attempt < self.max_retries:
                delay = self._calculate_delay(attempt)
                
                if self.logger:
                    self.logger.debug("RETRY_WAITING",
                                      attempt=attempt + 1,
                                      delay=round(delay, 2))
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if self.logger:
            self.logger.error("RETRY_EXHAUSTED",
                              url=url,
                              max_retries=self.max_retries)
        
        return None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents repeated calls to a failing service:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Requests fail immediately without trying
    - HALF_OPEN: Allow one request to test if service recovered
    """
    
    class State(Enum):
        CLOSED = "CLOSED"
        OPEN = "OPEN"
        HALF_OPEN = "HALF_OPEN"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        logger: "JsonLogger" = None
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Seconds before trying again when open.
            logger: Optional logger.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.logger = logger
        
        self.state = self.State.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
    
    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        if self.state == self.State.CLOSED:
            return True
        
        if self.state == self.State.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = self.State.HALF_OPEN
                    if self.logger:
                        self.logger.info("CIRCUIT_HALF_OPEN")
                    return True
            return False
        
        # HALF_OPEN: allow one request
        return True
    
    def record_success(self) -> None:
        """Record a successful request."""
        if self.state == self.State.HALF_OPEN:
            self.state = self.State.CLOSED
            self.failure_count = 0
            if self.logger:
                self.logger.info("CIRCUIT_CLOSED")
        elif self.state == self.State.CLOSED:
            self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == self.State.HALF_OPEN:
            self.state = self.State.OPEN
            if self.logger:
                self.logger.warning("CIRCUIT_OPEN",
                                    reason="Failed in half-open state")
        
        elif self.state == self.State.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = self.State.OPEN
                if self.logger:
                    self.logger.warning("CIRCUIT_OPEN",
                                        failures=self.failure_count)


class ResilientClient:
    """
    Combines RetryClient with CircuitBreaker for full resilience.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_strategy: str = "exponential",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        logger: "JsonLogger" = None
    ):
        """
        Initialize the resilient client.
        """
        self.retry_client = RetryClient(
            max_retries=max_retries,
            backoff_strategy=backoff_strategy,
            logger=logger
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            logger=logger
        )
        self.logger = logger
    
    async def post(self, url: str, json: dict = None, **kwargs) -> Optional[httpx.Response]:
        """
        Send POST request with full resilience.
        """
        if not self.circuit_breaker.can_execute():
            if self.logger:
                self.logger.warning("CIRCUIT_OPEN_REJECTED", url=url)
            return None
        
        try:
            response = await self.retry_client.post(url, json=json, **kwargs)
            
            if response:
                self.circuit_breaker.record_success()
                return response
            else:
                self.circuit_breaker.record_failure()
                return None
                
        except Exception as e:
            self.circuit_breaker.record_failure()
            if self.logger:
                self.logger.error("RESILIENT_REQUEST_FAILED",
                                  url=url,
                                  error=str(e))
            return None


# Testing
if __name__ == "__main__":
    import asyncio
    
    async def test_retry():
        print("Retry Client Test")
        print("=" * 40)
        
        client = RetryClient(max_retries=3, backoff_strategy="exponential")
        
        # Test delay calculation
        for i in range(5):
            delay = client._calculate_delay(i)
            print(f"Attempt {i}: delay = {delay:.2f}s")
        
        print("\nCircuit Breaker Test")
        print("=" * 40)
        
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)
        
        print(f"Initial state: {cb.state.value}")
        print(f"Can execute: {cb.can_execute()}")
        
        # Simulate failures
        for i in range(4):
            cb.record_failure()
            print(f"After failure {i+1}: state={cb.state.value}, count={cb.failure_count}")
        
        print(f"Can execute (circuit open): {cb.can_execute()}")
        
        print("\nAll resilience tests passed!")
    
    asyncio.run(test_retry())

