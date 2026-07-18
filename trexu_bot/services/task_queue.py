from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from itertools import count
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueueJob:
    job_id: str
    priority: int
    order: int
    description: str
    coro_factory: Callable[[], Awaitable[Any]]
    created_at: float = field(default_factory=time.time)


class DownloadQueueService:
    def __init__(self, worker_count: int = 2) -> None:
        self.worker_count = max(1, worker_count)
        self.queue: asyncio.PriorityQueue[tuple[int, int, QueueJob]] = asyncio.PriorityQueue()
        self._workers: list[asyncio.Task[Any]] = []
        self._counter = count(1)
        self._active_jobs: dict[str, QueueJob] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        for index in range(self.worker_count):
            task = asyncio.create_task(self._worker_loop(index + 1), name=f'download-worker-{index + 1}')
            self._workers.append(task)
        logger.info('Download queue started with %s worker(s)', self.worker_count)

    async def stop(self) -> None:
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._workers.clear()
        self._started = False
        logger.info('Download queue stopped')

    async def enqueue(
        self,
        *,
        job_id: str,
        vip: bool,
        description: str,
        coro_factory: Callable[[], Awaitable[Any]],
    ) -> int:
        if not self._started:
            await self.start()
        order = next(self._counter)
        priority = 0 if vip else 1
        job = QueueJob(
            job_id=job_id,
            priority=priority,
            order=order,
            description=description,
            coro_factory=coro_factory,
        )
        waiting_before = self.queue.qsize() + len(self._active_jobs)
        await self.queue.put((priority, order, job))
        logger.info('Enqueued job=%s vip=%s desc=%s position~%s', job_id, vip, description, waiting_before + 1)
        return waiting_before + 1

    def stats(self) -> dict[str, int]:
        return {
            'workers': self.worker_count,
            'waiting': self.queue.qsize(),
            'active': len(self._active_jobs),
            'total': self.queue.qsize() + len(self._active_jobs),
        }

    async def _worker_loop(self, worker_no: int) -> None:
        while True:
            _priority, _order, job = await self.queue.get()
            self._active_jobs[job.job_id] = job
            logger.info('Worker %s started job=%s desc=%s', worker_no, job.job_id, job.description)
            try:
                await job.coro_factory()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('Queue job failed: %s', job.job_id)
            finally:
                self._active_jobs.pop(job.job_id, None)
                self.queue.task_done()
                logger.info('Worker %s finished job=%s', worker_no, job.job_id)
