import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

logger = logging.getLogger("stream-manager")


class SSEStreamManager:
    """Manages active Client connection queues for Server-Sent Events (SSE)."""

    def __init__(self) -> None:
        # Maps connection_id -> asyncio.Queue containing formatted SSE text strings
        self._queues: dict[str, asyncio.Queue[str]] = {}
        # Maps connection_id -> list of raw events (dict) for polling fallback
        self._history: dict[str, list[dict[str, Any]]] = {}
        # Mutex lock to manage concurrent updates to the queues map
        self._lock = asyncio.Lock()

    async def register_connection(self, connection_id: str) -> None:
        """Allocates an asynchronous queue for a new connection ID."""
        async with self._lock:
            if connection_id not in self._queues:
                self._queues[connection_id] = asyncio.Queue(maxsize=100)
                logger.info(f"SSE Queue created for connection: {connection_id}")
            if connection_id not in self._history:
                self._history[connection_id] = []

    async def unregister_connection(self, connection_id: str) -> None:
        """Removes the queue for the specified connection ID."""
        async with self._lock:
            if connection_id in self._queues:
                del self._queues[connection_id]
                logger.info(f"SSE Queue cleaned up for connection: {connection_id}")

    async def _delayed_cleanup(self, connection_id: str, delay: float = 300.0) -> None:
        """Asynchronously cleans up the history buffer after a specified delay."""
        await asyncio.sleep(delay)
        async with self._lock:
            if connection_id in self._history:
                del self._history[connection_id]
                logger.info(f"SSE event history cleaned up for connection: {connection_id}")

    async def get_history(self, connection_id: str) -> list[dict[str, Any]]:
        """Retrieves the accumulated event history for the specified connection ID."""
        async with self._lock:
            return list(self._history.get(connection_id, []))

    async def publish_event(self, connection_id: str, event_name: str, data: Any) -> bool:
        """Pushes serialized SSE data to the connection's queue."""
        async with self._lock:
            # Initialize history buffer if it doesn't exist
            if connection_id not in self._history:
                self._history[connection_id] = []
            self._history[connection_id].append({"event": event_name, "data": data})

            if event_name in ("complete", "error"):
                # Clean up history after 5 minutes (300 seconds)
                asyncio.create_task(self._delayed_cleanup(connection_id))

            queue = self._queues.get(connection_id)
            if not queue:
                logger.warning(f"Publishing event '{event_name}' to history only for connection: {connection_id} (no active SSE client)")
                return True

        # Format as standard Server-Sent Event block
        json_data = json.dumps(data)
        sse_event = f"event: {event_name}\ndata: {json_data}\n\n"

        try:
            # Add to queue without blocking. If full, log error.
            queue.put_nowait(sse_event)
            logger.info(f"Published event '{event_name}' to connection {connection_id}")
            return True
        except asyncio.QueueFull:
            logger.error(f"SSE Queue full for connection: {connection_id}. Event dropped.")
            return False

    async def subscribe(self, connection_id: str) -> AsyncGenerator[str, None]:
        """Provides an asynchronous stream generator of SSE events for a connection."""
        await self.register_connection(connection_id)

        try:
            while True:
                # Wait for events to arrive in the queue
                async with self._lock:
                    queue = self._queues.get(connection_id)
                    if not queue:
                        # Queue was cleaned up, stop subscription
                        break

                event = await queue.get()
                yield event
                queue.task_done()
        except asyncio.CancelledError:
            logger.info(f"SSE Client connection cancelled: {connection_id}")
        finally:
            await self.unregister_connection(connection_id)


# Global singleton instance
stream_manager = SSEStreamManager()


def get_stream_manager() -> SSEStreamManager:
    """Dependency injection helper returning the global SSEStreamManager."""
    return stream_manager
