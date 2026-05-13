"""
Scheduler module for Nobitex Quant Trader.

Manages scheduled tasks, periodic data updates, and system timing.
"""

import asyncio
import schedule
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from app.logger import get_logger

logger = get_logger("nobitex_trader.scheduler")


class SchedulePolicy(str, Enum):
    """Scheduling policies for tasks."""
    INTERVAL = "interval"           # Run at fixed intervals
    CRON = "cron"                   # Cron-like scheduling
    ONCE = "once"                   # Run once at specific time
    PERIODIC = "periodic"           # Run during specific time windows
    EVENT_DRIVEN = "event_driven"   # Run on specific events


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    name: str
    func: Callable
    policy: SchedulePolicy
    interval_seconds: Optional[int] = None
    cron_expression: Optional[str] = None
    run_at: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    max_executions: Optional[int] = None
    execution_count: int = 0
    enabled: bool = True
    async_task: bool = False
    kwargs: Dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: f"task_{id(time.time())}")

    def should_run(self) -> bool:
        """Check if the task should run now."""
        if not self.enabled:
            return False

        if self.max_executions and self.execution_count >= self.max_executions:
            return False

        if self.run_at:
            return datetime.now() >= self.run_at

        if self.start_time and datetime.now() < self.start_time:
            return False

        if self.end_time and datetime.now() > self.end_time:
            return False

        return True


class TaskResult:
    """Stores the result of a task execution."""

    def __init__(self, task_name: str):
        """Initialize task result."""
        self.task_name = task_name
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.execution_count: int = 0
        self.last_result: Any = None
        self.last_error: Optional[Exception] = None
        self.execution_history: List[Dict[str, Any]] = []

    def record_execution(
        self,
        result: Any = None,
        error: Optional[Exception] = None,
        duration: float = 0,
    ):
        """Record a task execution."""
        self.last_run = datetime.now()
        self.execution_count += 1
        self.last_result = result
        self.last_error = error

        self.execution_history.append({
            "run_at": self.last_run.isoformat(),
            "result": str(result) if result else None,
            "error": str(error) if error else None,
            "duration_seconds": duration,
        })

        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]


class Scheduler:
    """
    Task scheduler for the trading system.
    
    Manages periodic tasks like:
    - Market data updates
    - Strategy evaluation
    - Risk checks
    - Portfolio rebalancing
    - System health checks
    """

    def __init__(self):
        """Initialize the scheduler."""
        self._tasks: Dict[str, ScheduledTask] = {}
        self._results: Dict[str, TaskResult] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._async_tasks: List[asyncio.Task] = []
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        # System timing
        self._start_time: Optional[datetime] = None
        self._uptime_seconds: float = 0

        logger.info("Scheduler initialized")

    def start(self):
        """Start the scheduler."""
        self._running = True
        self._start_time = datetime.now()
        # Capture the current event loop for async task scheduling
        try:
            self._event_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Scheduler stopped")

    def schedule_interval(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        async_task: bool = False,
        max_executions: Optional[int] = None,
        start_after: Optional[timedelta] = None,
        **kwargs,
    ) -> str:
        """
        Schedule a task to run at fixed intervals.

        Args:
            name: Unique task name
            func: Function to execute
            interval_seconds: Interval in seconds
            async_task: Whether to run as async task
            max_executions: Maximum number of executions (None for unlimited)
            start_after: Delay before first execution
            **kwargs: Additional arguments for the function

        Returns:
            Task ID
        """
        task = ScheduledTask(
            name=name,
            func=func,
            policy=SchedulePolicy.INTERVAL,
            interval_seconds=interval_seconds,
            max_executions=max_executions,
            async_task=async_task,
            kwargs=kwargs,
        )

        if start_after:
            task.run_at = datetime.now() + start_after

        self._tasks[name] = task
        self._results[name] = TaskResult(name)
        logger.info(
            f"Scheduled task '{name}' at {interval_seconds}s interval"
        )
        return task.task_id

    def schedule_once(
        self,
        name: str,
        func: Callable,
        run_at: datetime,
        **kwargs,
    ) -> str:
        """Schedule a task to run once at a specific time."""
        task = ScheduledTask(
            name=name,
            func=func,
            policy=SchedulePolicy.ONCE,
            run_at=run_at,
            kwargs=kwargs,
        )

        self._tasks[name] = task
        self._results[name] = TaskResult(name)
        logger.info(f"Scheduled one-time task '{name}' at {run_at}")
        return task.task_id

    def schedule_periodic(
        self,
        name: str,
        func: Callable,
        start_time: time,
        end_time: time,
        interval_seconds: int = 60,
        **kwargs,
    ) -> str:
        """Schedule a task to run during specific time windows."""
        task = ScheduledTask(
            name=name,
            func=func,
            policy=SchedulePolicy.PERIODIC,
            start_time=datetime.combine(datetime.now(), start_time),
            end_time=datetime.combine(datetime.now(), end_time),
            interval_seconds=interval_seconds,
            kwargs=kwargs,
        )

        self._tasks[name] = task
        self._results[name] = TaskResult(name)
        logger.info(
            f"Scheduled periodic task '{name}' "
            f"from {start_time} to {end_time}"
        )
        return task.task_id

    def unschedule(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self._tasks:
            self._tasks[name].enabled = False
            del self._tasks[name]
            logger.info(f"Removed scheduled task '{name}'")
            return True
        return False

    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a scheduled task."""
        if name not in self._tasks:
            return None

        task = self._tasks[name]
        result = self._results.get(name)

        return {
            "name": task.name,
            "task_id": task.task_id,
            "enabled": task.enabled,
            "policy": task.policy.value,
            "execution_count": task.execution_count,
            "last_run": result.last_run.isoformat() if result and result.last_run else None,
            "next_run": result.next_run.isoformat() if result and result.next_run else None,
            "last_error": str(result.last_error) if result and result.last_error else None,
        }

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all scheduled tasks."""
        return {name: self.get_task_status(name) for name in self._tasks}

    def get_task_result(self, name: str) -> Optional[TaskResult]:
        """Get the result object for a task."""
        return self._results.get(name)

    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        if self._start_time:
            return (datetime.now() - self._start_time).total_seconds()
        return 0

    def _run_loop(self):
        """Main scheduler loop."""
        logger.debug("Scheduler run loop started")

        while self._running:
            now = datetime.now()
            tasks_to_run = []

            for name, task in self._tasks.items():
                if task.should_run():
                    tasks_to_run.append(task)

            for task in tasks_to_run:
                self._execute_task(task)

            # Update next run times
            for name, task in self._tasks.items():
                if task.enabled and name in self._results:
                    result = self._results[name]
                    if task.policy == SchedulePolicy.INTERVAL:
                        if result.last_run:
                            result.next_run = result.last_run + timedelta(
                                seconds=task.interval_seconds
                            )
                        else:
                            result.next_run = now + timedelta(
                                seconds=task.interval_seconds
                            )

            time.sleep(0.5)  # Main loop sleep

        logger.debug("Scheduler run loop stopped")

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        result = self._results.get(task.name)

        try:
            start_time = time.time()
            logger.debug(f"Executing task: {task.name}")

            if task.async_task:
                # Schedule async execution on the main event loop
                if self._event_loop and self._event_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self._run_async_task(task), self._event_loop
                    )
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        logger.error(f"Async task error for '{task.name}': {e}")
                        if result:
                            result.record_execution(error=e)
                    task.execution_count += 1
                else:
                    logger.error(
                        f"No running event loop for async task '{task.name}'"
                    )
            else:
                result.record_execution(
                    result=task.func(**task.kwargs),
                    duration=time.time() - start_time,
                )
                task.execution_count += 1
                logger.debug(f"Task executed: {task.name}")

        except Exception as e:
            logger.error(f"Task execution error for '{task.name}': {e}")
            if result:
                result.record_execution(error=e)

    async def _run_async_task(self, task: ScheduledTask):
        """Run an async task."""
        result = self._results.get(task.name)
        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(task.func):
                await task.func(**task.kwargs)
            else:
                task.func(**task.kwargs)

            task.execution_count += 1
            if result:
                result.record_execution(
                    duration=time.time() - start_time,
                )

        except Exception as e:
            logger.error(f"Async task error for '{task.name}': {e}")
            if result:
                result.record_execution(error=e)

    def reset(self):
        """Reset the scheduler."""
        self.stop()
        self._tasks.clear()
        self._results.clear()
        self._async_tasks.clear()
        self._start_time = None
        logger.info("Scheduler reset")


class TradingSchedule:
    """
    Manages trading schedules and market hours.
    
    Handles market open/close times, holidays, and trading windows.
    """

    def __init__(self, trading_hours: Optional[Dict] = None):
        """
        Initialize trading schedule.

        Args:
            trading_hours: Custom trading hours configuration
        """
        self._trading_hours = trading_hours or {
            "market_open": time(0, 0),   # Crypto markets are 24/7
            "market_close": time(23, 59),
            "trading_windows": [
                {"start": time(0, 0), "end": time(23, 59), "enabled": True},
            ],
        }
        self._holidays: List[datetime] = []
        self._paused = False

    def is_trading_allowed(self) -> bool:
        """Check if trading is currently allowed."""
        if self._paused:
            return False

        now = datetime.now()
        current_time = now.time()

        for window in self._trading_hours.get("trading_windows", []):
            if (window["start"] <= current_time <= window["end"]
                    and window.get("enabled", True)):
                return True

        return False

    def is_holiday(self, date: Optional[datetime] = None) -> bool:
        """Check if a date is a holiday."""
        if date is None:
            date = datetime.now()

        return date in self._holidays

    def add_holiday(self, date: datetime):
        """Add a holiday to the schedule."""
        self._holidays.append(date)

    def pause_trading(self):
        """Pause all trading."""
        self._paused = True
        logger.warning("Trading paused by scheduler")

    def resume_trading(self):
        """Resume trading."""
        self._paused = False
        logger.info("Trading resumed by scheduler")

    def next_trading_window(self) -> Optional[Dict]:
        """Get the next trading window."""
        now = datetime.now()
        current_time = now.time()

        for window in self._trading_hours.get("trading_windows", []):
            if not window.get("enabled", True):
                continue

            start = datetime.combine(now.date(), window["start"])
            end = datetime.combine(now.date(), window["end"])

            if now < start:
                return {
                    "start": start,
                    "end": end,
                    "duration": (end - start).total_seconds(),
                }

        return None

    @property
    def is_paused(self) -> bool:
        """Check if trading is paused."""
        return self._paused
