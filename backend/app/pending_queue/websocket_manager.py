import asyncio
import json
from typing import Set

import structlog
from fastapi import WebSocket

from app.pending_queue.manager import PendingQueueManager

logger = structlog.get_logger()


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts queue events to connected clients.

    This provides real-time updates to the frontend without polling.
    """

    def __init__(self):
        """Initialize the WebSocket manager"""
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task: asyncio.Task | None = None
        self._queue_manager: PendingQueueManager | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("websocket_connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
        """
        self.active_connections.discard(websocket)
        logger.info("websocket_disconnected", total_connections=len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
        """
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error("websocket_send_failed", error=str(e))
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def start_broadcasting(self, queue_manager: PendingQueueManager) -> None:
        """
        Start listening to queue events and broadcasting to clients.

        Args:
            queue_manager: The queue manager to subscribe to
        """
        self._queue_manager = queue_manager

        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
            logger.info("broadcast_task_started")

    async def _broadcast_loop(self) -> None:
        """
        Internal loop that subscribes to queue events and broadcasts them.
        """
        try:
            async for event in self._queue_manager.subscribe_to_events():
                await self.broadcast(event)
        except asyncio.CancelledError:
            logger.info("broadcast_task_cancelled")
        except Exception as e:
            logger.error("broadcast_loop_error", error=str(e))

    async def stop_broadcasting(self) -> None:
        """Stop the broadcasting task"""
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            logger.info("broadcast_task_stopped")


# Global WebSocket manager instance
ws_manager = WebSocketManager()
