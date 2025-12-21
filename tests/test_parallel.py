"""
Unit tests for the parallel processing module.

Tests cover:
- ThreadSafeCounter
- ThreadSafeDict
- TaskQueue
- ParallelExecutor
- WorkerPool
- parallel_map_cpu
- parallel_map_io
"""

import unittest
import threading
import time
import sys
from pathlib import Path

# Add SHARED to path
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))


# Module-level function for multiprocessing (can be pickled)
def _cpu_work_for_test(x: int) -> int:
    """Simple CPU-bound work function for testing."""
    return sum(i * i for i in range(x))

from league_sdk.parallel import (
    ParallelConfig,
    TaskResult,
    ThreadSafeCounter,
    ThreadSafeDict,
    TaskQueue,
    ParallelExecutor,
    WorkerPool,
    parallel_map_cpu,
    parallel_map_io,
    get_cpu_count,
    get_recommended_thread_count,
    get_recommended_process_count,
)


class TestThreadSafeCounter(unittest.TestCase):
    """Tests for ThreadSafeCounter class."""

    def test_initial_value(self):
        """Test counter starts with correct initial value."""
        counter = ThreadSafeCounter()
        self.assertEqual(counter.get_value(), 0)

        counter = ThreadSafeCounter(100)
        self.assertEqual(counter.get_value(), 100)

    def test_increment(self):
        """Test incrementing counter."""
        counter = ThreadSafeCounter()
        self.assertEqual(counter.increment(), 1)
        self.assertEqual(counter.increment(), 2)
        self.assertEqual(counter.increment(5), 7)

    def test_decrement(self):
        """Test decrementing counter."""
        counter = ThreadSafeCounter(10)
        self.assertEqual(counter.decrement(), 9)
        self.assertEqual(counter.decrement(3), 6)

    def test_reset(self):
        """Test resetting counter."""
        counter = ThreadSafeCounter(100)
        counter.reset(50)
        self.assertEqual(counter.get_value(), 50)
        counter.reset()
        self.assertEqual(counter.get_value(), 0)

    def test_thread_safety(self):
        """Test counter is thread-safe under concurrent access."""
        counter = ThreadSafeCounter()
        num_threads = 10
        increments_per_thread = 1000

        def increment_many():
            for _ in range(increments_per_thread):
                counter.increment()

        threads = [threading.Thread(target=increment_many) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread
        self.assertEqual(counter.get_value(), expected)


class TestThreadSafeDict(unittest.TestCase):
    """Tests for ThreadSafeDict class."""

    def test_set_and_get(self):
        """Test setting and getting values."""
        d = ThreadSafeDict()
        d.set("key1", "value1")
        d.set("key2", 42)

        self.assertEqual(d.get("key1"), "value1")
        self.assertEqual(d.get("key2"), 42)
        self.assertIsNone(d.get("nonexistent"))
        self.assertEqual(d.get("nonexistent", "default"), "default")

    def test_delete(self):
        """Test deleting keys."""
        d = ThreadSafeDict()
        d.set("key1", "value1")

        self.assertTrue(d.delete("key1"))
        self.assertFalse(d.delete("key1"))  # Already deleted
        self.assertIsNone(d.get("key1"))

    def test_keys_values_items(self):
        """Test keys(), values(), and items() methods."""
        d = ThreadSafeDict()
        d.set("a", 1)
        d.set("b", 2)
        d.set("c", 3)

        self.assertEqual(sorted(d.keys()), ["a", "b", "c"])
        self.assertEqual(sorted(d.values()), [1, 2, 3])
        self.assertEqual(sorted(d.items()), [("a", 1), ("b", 2), ("c", 3)])

    def test_clear_and_len(self):
        """Test clear() and __len__()."""
        d = ThreadSafeDict()
        d.set("a", 1)
        d.set("b", 2)

        self.assertEqual(len(d), 2)
        d.clear()
        self.assertEqual(len(d), 0)

    def test_thread_safety(self):
        """Test dict is thread-safe under concurrent access."""
        d = ThreadSafeDict()
        num_threads = 10
        ops_per_thread = 100

        def concurrent_ops(thread_id):
            for i in range(ops_per_thread):
                key = f"thread_{thread_id}_key_{i}"
                d.set(key, i)
                d.get(key)

        threads = [threading.Thread(target=concurrent_ops, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have all keys
        expected_keys = num_threads * ops_per_thread
        self.assertEqual(len(d), expected_keys)


class TestTaskQueue(unittest.TestCase):
    """Tests for TaskQueue class."""

    def test_put_and_get(self):
        """Test basic put and get operations."""
        q = TaskQueue()
        q.put("task1")
        q.put("task2")

        self.assertEqual(q.size(), 2)
        self.assertEqual(q.get(), "task1")
        self.assertEqual(q.get(), "task2")
        self.assertTrue(q.is_empty())

    def test_processed_count(self):
        """Test processed count tracking."""
        q = TaskQueue()
        q.put("task1")
        q.put("task2")
        q.put("task3")

        self.assertEqual(q.processed_count(), 0)
        q.get()
        self.assertEqual(q.processed_count(), 1)
        q.get()
        self.assertEqual(q.processed_count(), 2)


class TestParallelConfig(unittest.TestCase):
    """Tests for ParallelConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ParallelConfig()
        self.assertIsNotNone(config.max_workers)
        self.assertGreater(config.max_workers, 0)
        self.assertEqual(config.timeout, 30.0)
        self.assertFalse(config.use_process_pool)
        self.assertEqual(config.chunk_size, 10)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ParallelConfig(
            max_workers=4,
            timeout=60.0,
            use_process_pool=True,
            chunk_size=20
        )
        self.assertEqual(config.max_workers, 4)
        self.assertEqual(config.timeout, 60.0)
        self.assertTrue(config.use_process_pool)
        self.assertEqual(config.chunk_size, 20)


class TestTaskResult(unittest.TestCase):
    """Tests for TaskResult dataclass."""

    def test_success_result(self):
        """Test successful task result."""
        result = TaskResult(
            task_id="task_1",
            success=True,
            result=42,
            duration_ms=100.5
        )
        self.assertEqual(result.task_id, "task_1")
        self.assertTrue(result.success)
        self.assertEqual(result.result, 42)
        self.assertIsNone(result.error)
        self.assertEqual(result.duration_ms, 100.5)

    def test_failure_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="task_2",
            success=False,
            error="Something went wrong",
            duration_ms=50.0
        )
        self.assertFalse(result.success)
        self.assertIsNone(result.result)
        self.assertEqual(result.error, "Something went wrong")


class TestParallelExecutor(unittest.TestCase):
    """Tests for ParallelExecutor class."""

    def test_submit_and_map(self):
        """Test submit and map operations with ThreadPoolExecutor."""
        config = ParallelConfig(max_workers=2, use_process_pool=False)

        def square(x):
            return x ** 2

        with ParallelExecutor(config) as executor:
            results = executor.map(square, [1, 2, 3, 4, 5])

        successful = [r for r in results if r.success]
        self.assertEqual(len(successful), 5)
        result_values = sorted([r.result for r in successful])
        self.assertEqual(result_values, [1, 4, 9, 16, 25])

    def test_executor_handles_errors(self):
        """Test executor properly handles errors in tasks."""
        config = ParallelConfig(max_workers=2)

        def failing_task(x):
            if x == 3:
                raise ValueError("Error on 3")
            return x

        with ParallelExecutor(config) as executor:
            results = executor.map(failing_task, [1, 2, 3, 4, 5])

        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        self.assertEqual(len(successes), 4)
        self.assertEqual(len(failures), 1)


class TestWorkerPool(unittest.TestCase):
    """Tests for WorkerPool class."""

    def test_worker_pool_basic(self):
        """Test basic worker pool operations."""
        results = []
        lock = threading.Lock()

        def handler(task):
            with lock:
                results.append(task * 2)
            return task * 2

        with WorkerPool(num_workers=2, task_handler=handler) as pool:
            for i in range(5):
                pool.submit(i)

            # Wait for processing
            time.sleep(0.5)

            task_results = pool.get_results()

        self.assertEqual(len(results), 5)
        self.assertEqual(sorted(results), [0, 2, 4, 6, 8])


class TestParallelMapFunctions(unittest.TestCase):
    """Tests for parallel_map_cpu and parallel_map_io functions."""

    def test_parallel_map_io(self):
        """Test parallel_map_io with I/O simulation."""
        def simulate_io(x):
            time.sleep(0.01)  # Simulate I/O
            return x ** 2

        start = time.time()
        results = parallel_map_io(simulate_io, list(range(10)), max_workers=5)
        duration = time.time() - start

        self.assertEqual(len(results), 10)
        self.assertEqual(sorted(results), [0, 1, 4, 9, 16, 25, 36, 49, 64, 81])
        # Parallel should be faster than sequential
        self.assertLess(duration, 0.15)  # 10 * 0.01 = 0.1 sequential

    def test_parallel_map_cpu(self):
        """Test parallel_map_cpu with CPU-bound work."""
        # Use module-level function (can be pickled for multiprocessing)
        results = parallel_map_cpu(_cpu_work_for_test, [10, 20, 30, 40], max_workers=2)

        self.assertEqual(len(results), 4)
        self.assertEqual(results[0], sum(i * i for i in range(10)))


class TestUtilityFunctions(unittest.TestCase):
    """Tests for utility functions."""

    def test_get_cpu_count(self):
        """Test get_cpu_count returns positive integer."""
        count = get_cpu_count()
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_get_recommended_thread_count(self):
        """Test recommended thread count is CPU * 2."""
        thread_count = get_recommended_thread_count()
        cpu_count = get_cpu_count()
        self.assertEqual(thread_count, cpu_count * 2)

    def test_get_recommended_process_count(self):
        """Test recommended process count equals CPU count."""
        process_count = get_recommended_process_count()
        cpu_count = get_cpu_count()
        self.assertEqual(process_count, cpu_count)


if __name__ == "__main__":
    unittest.main()
