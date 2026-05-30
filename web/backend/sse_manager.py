"""SSE connection pool — pub/sub per job_id."""

import asyncio
from collections import defaultdict


class SSEManager:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[job_id].append(queue)
        return queue

    async def publish(self, job_id: str, event: str, data: dict):
        for q in self._queues.get(job_id, []):
            try:
                await q.put((event, data))
            except Exception:
                pass

    async def unsubscribe(self, job_id: str, queue: asyncio.Queue):
        queues = self._queues.get(job_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._queues.pop(job_id, None)
