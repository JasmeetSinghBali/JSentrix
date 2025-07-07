"""
mcp_server/workers/task_registry.py

🧹 task_registry is meant for global task management that persists beyond stream-lifecycle (e.g., system-wide retries, cleanup workers)
A lightweight centralized task manager to track background tasks,
useful for graceful shutdowns in MCP server.

🚨 NOTE:
    Use it only when:
    - the agent runs indefinitely regardless of stream, like a log cleanup loop, or
    - it is spawning multi-agent control tasks across graphs, or
    - building one-off global tasks that shouldn't die quietly on shutdown.
Usage:
    from workers.task_registry import task_registry
    task_registry.add(asyncio.create_task(my_worker()))
    # or
    task_registry.add(my_worker())  # It will auto-wrap coroutine fn with create_task()

    # On shutdown, it cancels and awaits all tasks:
    await task_registry.shutdown()

"""

import asyncio
from typing import Set, Coroutine
from utils.logger import get_logger

logger = get_logger("task.registry")


class TaskRegistry:
    def __init__(self):
        self.tasks: Set[asyncio.Task] = set()

    def add(self, task_or_coro: Coroutine):
        """
        Add a coroutine or task to the registry.
        If it's a coroutine, wraps it in a task.
        """
        if asyncio.iscoroutine(task_or_coro):
            task = asyncio.create_task(task_or_coro)
        elif isinstance(task_or_coro, asyncio.Task):
            task = task_or_coro
        else:
            raise ValueError("Only coroutine or asyncio.Task objects can be registered")

        self.tasks.add(task)

        def _on_done(t):
            self.tasks.discard(t)

        task.add_done_callback(_on_done)

        logger.debug(f"✅ Task registered: {task.get_name() if hasattr(task, 'get_name') else str(task)}")

    async def shutdown(self):
        """
        Cancels all registered tasks and awaits their shutdown.
        Should be registered as a shutdown callback.
        """
        if not self.tasks:
            return

        logger.info(f"🛑 Cancelling {len(self.tasks)} registered background task(s)...")
        for task in self.tasks:
            task.cancel()

        results = await asyncio.gather(*self.tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error(f"⚠️ Task error during shutdown: {result}")

        logger.info("✅ All background tasks shutdown cleanly.")

        self.tasks.clear()


# Singleton instance
task_registry = TaskRegistry()