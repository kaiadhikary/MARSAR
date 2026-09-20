import asyncio
import json
from typing import Set, Dict, Any


class LocalEventBroadcaster:
    """
    In-memory asynchronous pub/sub event bus.
    Enables pipeline stages (ingestion, detection, scoring) to broadcast events
    to local UI subscribers and loggers without external message brokers (e.g., Redis).
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Subscribes a local consumer to the broadcast feed."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unregisters a consumer queue."""
        async with self._lock:
            self._subscribers.discard(queue)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """
        Dispatches an event payload to all active local listener queues.
        Drops messages if a queue buffer is saturated to prevent pipeline blocking.
        """
        message = {
            "event": event_type,
            "data": data
        }

        async with self._lock:
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    # Drop slow consumer event to maintain ingestion throughput
                    pass

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]):
        """Synchronous wrapper for dispatching events from standard worker threads."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(event_type, data))
            else:
                loop.run_until_complete(self.broadcast(event_type, data))
        except RuntimeError:
            pass


local_broadcaster = LocalEventBroadcaster()