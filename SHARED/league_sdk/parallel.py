"""
Parallel Processing Module - Multiprocessing and Multithreading utilities.

This module provides utilities for parallel processing in the MCP League System:
- Multiprocessing: For CPU-bound operations (heavy computations)
- Multithreading: For I/O-bound operations (network calls, file I/O)

Based on Chapter 16 of the Software Submission Guidelines V2.0:
- Multiprocessing is suited for CPU-bound operations
- Multithreading is suited for I/O-bound operations
- Thread safety is critical in multithreaded programs
"""

import os
import queue
import threading
import multiprocessing
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, Generic, List, Optional,
    TypeVar, Union, Tuple, Iterator
)
from functools import wraps
import time
import logging

# Type variables for generic parallel processing
T = TypeVar('T')
R = TypeVar('R')


@dataclass
class ParallelConfig:
    """
    Configuration for parallel processing.

    Attributes:
        max_workers: Maximum number of workers (threads/processes)
        timeout: Timeout for individual tasks in seconds
        use_process_pool: Use ProcessPoolExecutor instead of ThreadPoolExecutor
        chunk_size: Size of chunks for batch processing
    """
    max_workers: Optional[int] = None  # None = use cpu_count()
    timeout: float = 30.0
    use_process_pool: bool = False
    chunk_size: int = 10

    def __post_init__(self):
        """Set default max_workers based on CPU count if not specified."""
        if self.max_workers is None:
            self.max_workers = multiprocessing.cpu_count()


@dataclass
class TaskResult(Generic[T]):
    """
    Result of a parallel task execution.

    Attributes:
        task_id: Unique identifier for the task
        success: Whether the task completed successfully
        result: The result value if successful
        error: Error message if failed
        duration_ms: Execution time in milliseconds
    """
    task_id: str
    success: bool
    result: Optional[T] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class ThreadSafeCounter:
    """
    Thread-safe counter using locks.

    Demonstrates proper synchronization using locks to protect shared state.
    """

    def __init__(self, initial_value: int = 0):
        """Initialize counter with a starting value."""
        self._value = initial_value
        self._lock = threading.Lock()

    def increment(self, amount: int = 1) -> int:
        """
        Atomically increment the counter.

        Args:
            amount: Amount to increment by

        Returns:
            New counter value
        """
        with self._lock:
            self._value += amount
            return self._value

    def decrement(self, amount: int = 1) -> int:
        """
        Atomically decrement the counter.

        Args:
            amount: Amount to decrement by

        Returns:
            New counter value
        """
        with self._lock:
            self._value -= amount
            return self._value

    def get_value(self) -> int:
        """Get the current counter value."""
        with self._lock:
            return self._value

    def reset(self, value: int = 0) -> None:
        """Reset the counter to a specific value."""
        with self._lock:
            self._value = value


class ThreadSafeDict(Generic[T]):
    """
    Thread-safe dictionary wrapper using RLock.

    Demonstrates using reentrant locks for nested locking scenarios.
    """

    def __init__(self):
        """Initialize an empty thread-safe dictionary."""
        self._data: Dict[str, T] = {}
        self._lock = threading.RLock()

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get a value by key.

        Args:
            key: The key to look up
            default: Default value if key not found

        Returns:
            The value or default
        """
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: T) -> None:
        """
        Set a value for a key.

        Args:
            key: The key to set
            value: The value to store
        """
        with self._lock:
            self._data[key] = value

    def delete(self, key: str) -> bool:
        """
        Delete a key from the dictionary.

        Args:
            key: The key to delete

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def keys(self) -> List[str]:
        """Get all keys."""
        with self._lock:
            return list(self._data.keys())

    def values(self) -> List[T]:
        """Get all values."""
        with self._lock:
            return list(self._data.values())

    def items(self) -> List[Tuple[str, T]]:
        """Get all key-value pairs."""
        with self._lock:
            return list(self._data.items())

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        """Get the number of entries."""
        with self._lock:
            return len(self._data)


class TaskQueue(Generic[T]):
    """
    Thread-safe task queue for producer-consumer pattern.

    Demonstrates using queue.Queue for safe data passing between threads.
    """

    def __init__(self, maxsize: int = 0):
        """
        Initialize a task queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)
        self._processed_count = ThreadSafeCounter()

    def put(self, item: T, block: bool = True, timeout: Optional[float] = None) -> None:
        """
        Add an item to the queue.

        Args:
            item: Item to add
            block: Whether to block if queue is full
            timeout: Timeout for blocking
        """
        self._queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: Optional[float] = None) -> T:
        """
        Get an item from the queue.

        Args:
            block: Whether to block if queue is empty
            timeout: Timeout for blocking

        Returns:
            The next item from the queue

        Raises:
            queue.Empty: If queue is empty and not blocking
        """
        item = self._queue.get(block=block, timeout=timeout)
        self._processed_count.increment()
        return item

    def task_done(self) -> None:
        """Mark a task as done (for join() to work properly)."""
        self._queue.task_done()

    def join(self) -> None:
        """Wait for all tasks to be processed."""
        self._queue.join()

    def size(self) -> int:
        """Get the current queue size."""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def processed_count(self) -> int:
        """Get the number of processed items."""
        return self._processed_count.get_value()


class ParallelExecutor:
    """
    Unified executor for parallel task processing.

    Automatically selects between ThreadPoolExecutor and ProcessPoolExecutor
    based on configuration. Handles task submission, result collection,
    and error handling.
    """

    def __init__(self, config: Optional[ParallelConfig] = None):
        """
        Initialize the parallel executor.

        Args:
            config: Configuration for parallel processing
        """
        self.config = config or ParallelConfig()
        self._executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None
        self._results: ThreadSafeDict[TaskResult] = ThreadSafeDict()
        self._task_counter = ThreadSafeCounter()

    def __enter__(self):
        """Context manager entry - create executor."""
        if self.config.use_process_pool:
            self._executor = ProcessPoolExecutor(max_workers=self.config.max_workers)
        else:
            self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - shutdown executor."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def submit(
        self,
        func: Callable[..., T],
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Submit a task for parallel execution.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            task_id: Optional custom task ID
            **kwargs: Keyword arguments for the function

        Returns:
            Task ID for tracking the result
        """
        if not self._executor:
            raise RuntimeError("Executor not initialized. Use context manager.")

        if task_id is None:
            task_id = f"task_{self._task_counter.increment()}"

        def wrapped_func():
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                return TaskResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    duration_ms=duration_ms
                )
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    duration_ms=duration_ms
                )

        future = self._executor.submit(wrapped_func)
        future.add_done_callback(lambda f: self._results.set(task_id, f.result()))

        return task_id

    def map(
        self,
        func: Callable[[T], R],
        items: List[T],
        timeout: Optional[float] = None
    ) -> List[TaskResult[R]]:
        """
        Apply a function to multiple items in parallel.

        Args:
            func: Function to apply to each item
            items: List of items to process
            timeout: Timeout for all operations

        Returns:
            List of TaskResult objects
        """
        if not self._executor:
            raise RuntimeError("Executor not initialized. Use context manager.")

        timeout = timeout or self.config.timeout
        results: List[TaskResult[R]] = []

        futures = []
        for i, item in enumerate(items):
            task_id = f"map_{i}"

            def create_task(item_copy, tid):
                def task():
                    start_time = time.time()
                    try:
                        result = func(item_copy)
                        duration_ms = (time.time() - start_time) * 1000
                        return TaskResult(
                            task_id=tid,
                            success=True,
                            result=result,
                            duration_ms=duration_ms
                        )
                    except Exception as e:
                        duration_ms = (time.time() - start_time) * 1000
                        return TaskResult(
                            task_id=tid,
                            success=False,
                            error=str(e),
                            duration_ms=duration_ms
                        )
                return task

            future = self._executor.submit(create_task(item, task_id))
            futures.append(future)

        for future in as_completed(futures, timeout=timeout):
            try:
                results.append(future.result())
            except Exception as e:
                results.append(TaskResult(
                    task_id="unknown",
                    success=False,
                    error=str(e)
                ))

        return results

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Get the result of a submitted task.

        Args:
            task_id: The task ID returned by submit()

        Returns:
            TaskResult if available, None if not yet completed
        """
        return self._results.get(task_id)


def run_in_thread(func: Callable[..., T]) -> Callable[..., threading.Thread]:
    """
    Decorator to run a function in a separate thread.

    Example:
        @run_in_thread
        def long_running_task():
            # This runs in a separate thread
            pass

        thread = long_running_task()
        thread.join()  # Wait for completion
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> threading.Thread:
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper


def run_in_process(func: Callable[..., T]) -> Callable[..., multiprocessing.Process]:
    """
    Decorator to run a function in a separate process.

    Example:
        @run_in_process
        def cpu_intensive_task():
            # This runs in a separate process
            pass

        process = cpu_intensive_task()
        process.join()  # Wait for completion
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> multiprocessing.Process:
        process = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        process.start()
        return process
    return wrapper


class WorkerPool:
    """
    A reusable pool of worker threads for I/O-bound operations.

    Implements the producer-consumer pattern with a task queue
    and multiple worker threads.
    """

    def __init__(
        self,
        num_workers: int = 4,
        task_handler: Optional[Callable[[Any], Any]] = None
    ):
        """
        Initialize the worker pool.

        Args:
            num_workers: Number of worker threads
            task_handler: Function to process each task
        """
        self.num_workers = num_workers
        self.task_handler = task_handler
        self.task_queue: TaskQueue[Any] = TaskQueue()
        self.result_queue: TaskQueue[TaskResult] = TaskQueue()
        self._workers: List[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()

    def _worker(self):
        """Worker thread main loop."""
        while self._running:
            try:
                task = self.task_queue.get(block=True, timeout=0.1)

                start_time = time.time()
                task_id = task.get('task_id', 'unknown') if isinstance(task, dict) else 'unknown'

                try:
                    if self.task_handler:
                        result = self.task_handler(task)
                    else:
                        result = task  # No handler, return task as-is

                    duration_ms = (time.time() - start_time) * 1000
                    self.result_queue.put(TaskResult(
                        task_id=str(task_id),
                        success=True,
                        result=result,
                        duration_ms=duration_ms
                    ))
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.result_queue.put(TaskResult(
                        task_id=str(task_id),
                        success=False,
                        error=str(e),
                        duration_ms=duration_ms
                    ))
                finally:
                    self.task_queue.task_done()

            except queue.Empty:
                continue

    def start(self) -> None:
        """Start all worker threads."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._workers = []

            for i in range(self.num_workers):
                worker = threading.Thread(
                    target=self._worker,
                    name=f"WorkerPool-{i}",
                    daemon=True
                )
                worker.start()
                self._workers.append(worker)

    def stop(self, wait: bool = True) -> None:
        """
        Stop all worker threads.

        Args:
            wait: Whether to wait for pending tasks to complete
        """
        with self._lock:
            self._running = False

            if wait:
                self.task_queue.join()

            for worker in self._workers:
                worker.join(timeout=1.0)

            self._workers.clear()

    def submit(self, task: Any) -> None:
        """
        Submit a task for processing.

        Args:
            task: The task to process
        """
        if not self._running:
            raise RuntimeError("Worker pool not running. Call start() first.")
        self.task_queue.put(task)

    def get_results(self, block: bool = False) -> List[TaskResult]:
        """
        Get all available results.

        Args:
            block: Whether to wait if no results available

        Returns:
            List of TaskResult objects
        """
        results = []
        while True:
            try:
                result = self.result_queue.get(block=False)
                results.append(result)
            except queue.Empty:
                break
        return results

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def parallel_map_cpu(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None,
    chunk_size: int = 1
) -> List[R]:
    """
    Apply a function to items in parallel using multiprocessing.

    Best for CPU-bound operations like:
    - Heavy mathematical computations
    - Image processing
    - Data transformation

    Args:
        func: Function to apply to each item (must be picklable)
        items: List of items to process
        max_workers: Maximum number of processes (default: CPU count)
        chunk_size: Number of items per process batch

    Returns:
        List of results in the same order as inputs

    Example:
        def expensive_computation(x):
            return x ** 2

        results = parallel_map_cpu(expensive_computation, [1, 2, 3, 4])
    """
    max_workers = max_workers or multiprocessing.cpu_count()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(func, items, chunksize=chunk_size))

    return results


def parallel_map_io(
    func: Callable[[T], R],
    items: List[T],
    max_workers: Optional[int] = None
) -> List[R]:
    """
    Apply a function to items in parallel using threading.

    Best for I/O-bound operations like:
    - Network requests
    - File I/O
    - Database queries

    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of threads (default: CPU count * 2)

    Returns:
        List of results in the same order as inputs

    Example:
        def fetch_url(url):
            return requests.get(url).status_code

        results = parallel_map_io(fetch_url, ['http://a.com', 'http://b.com'])
    """
    max_workers = max_workers or (multiprocessing.cpu_count() * 2)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(func, items))

    return results


# Module-level convenience functions for common patterns

def get_cpu_count() -> int:
    """Get the number of available CPU cores."""
    return multiprocessing.cpu_count()


def get_recommended_thread_count() -> int:
    """Get recommended number of threads for I/O operations."""
    return multiprocessing.cpu_count() * 2


def get_recommended_process_count() -> int:
    """Get recommended number of processes for CPU operations."""
    return multiprocessing.cpu_count()
