"""
Server-Sent Events (SSE) Manager for one-way server-to-client real-time updates.

This replaces the WebSocket implementation for the meal generation notification use case,
which only requires one-way communication (server → client).
"""

import asyncio
import json
import os
from typing import Dict, Optional
from fastapi import Request
from starlette.responses import StreamingResponse
import redis.asyncio as redis
from app.logger import get_logger

logger = get_logger("sse_manager")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class SSEManager:
    """
    Manages SSE connections for users. Each user can have one active SSE connection.
    """
    
    def __init__(self):
        self._queues: Dict[int, asyncio.Queue] = {}
        self._connection_count = 0
    
    async def subscribe_user(self, user_id: int) -> asyncio.Queue:
        """
        Subscribe a user to receive SSE events.
        
        Creates a new queue for this user. If the user already has a queue,
        the old one is replaced (new connection takes precedence).
        
        Args:
            user_id: The user's ID
            
        Returns:
            An asyncio.Queue that will receive events for this user
        """
        # If there's an existing queue, we don't need to close it explicitly
        # The old connection's generator will detect the disconnect and clean up
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[user_id] = queue
        self._connection_count += 1
        
        logger.info("User subscribed to SSE", extra={
            "user_id": user_id,
            "total_connections": self._connection_count
        })
        
        return queue
    
    def unsubscribe_user(self, user_id: int):
        """
        Unsubscribe a user from SSE events.
        Called when the client disconnects.
        """
        if user_id in self._queues:
            del self._queues[user_id]
            self._connection_count -= 1
            
            logger.info("User unsubscribed from SSE", extra={
                "user_id": user_id,
                "total_connections": self._connection_count
            })
    
    async def send_to_user(self, user_id: int, event_type: str, data: Optional[dict] = None):
        """
        Send an event to a specific user.
        
        Args:
            user_id: The target user's ID
            event_type: The event name (e.g., "meal_ready")
            data: Optional JSON-serializable data to include
        """
        queue = self._queues.get(user_id)
        if queue:
            event = {
                "event": event_type,
                "data": data or {}
            }
            await queue.put(event)
            
            logger.debug("SSE event sent to user", extra={
                "user_id": user_id,
                "event_type": event_type
            })
        else:
            logger.debug("No active SSE connection for user", extra={
                "user_id": user_id,
                "event_type": event_type
            })


# Global singleton instance
sse_manager = SSEManager()


async def redis_listener():
    """
    Background task that listens for Redis pub/sub messages and forwards them
    to connected SSE clients.
    
    This replaces the WebSocket-based Redis listener with SSE-based delivery.
    """
    logger.info("Starting Redis listener for SSE", extra={"url": REDIS_URL})
    
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("mealGenerated")
        
        logger.info("Successfully subscribed to mealGenerated channel for SSE")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    user_id = data["userId"]
                    
                    logger.info("Meal ready event received, forwarding via SSE", extra={
                        "user_id": user_id
                    })
                    
                    # Forward to SSE manager
                    await sse_manager.send_to_user(user_id, "meal_ready", {"userId": user_id})
                    
                except Exception as e:
                    logger.error(f"Error processing Redis message for SSE: {str(e)}")
                    
    except Exception as e:
        logger.critical(f"Redis Connection Failed for SSE: {str(e)}")


def create_sse_response(user_id: int, request: Request) -> StreamingResponse:
    """
    Create a StreamingResponse that delivers SSE events to the client.
    
    Args:
        user_id: The authenticated user's ID
        request: The FastAPI request object (used to detect disconnects)
        
    Returns:
        A StreamingResponse with the SSE stream
    """
    
    async def event_generator():
        """Generate SSE-formatted events from the user's queue."""
        queue = await sse_manager.subscribe_user(user_id)
        
        try:
            # Send an initial connection established event
            yield f"event: connected\ndata: {json.dumps({'userId': user_id})}\n\n"
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("Client disconnected from SSE", extra={"user_id": user_id})
                    break
                
                try:
                    # Wait for events with a timeout to periodically check disconnect
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE (event name + data + double newline)
                    event_name = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    
                    yield f"event: {event_name}\ndata: {event_data}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send a heartbeat comment to keep connection alive
                    # This also helps detect broken connections
                    yield ":heartbeat\n\n"
                    continue
                    
        except asyncio.CancelledError:
            logger.info("SSE generator cancelled", extra={"user_id": user_id})
            raise
        except Exception as e:
            logger.error(f"Error in SSE generator: {str(e)}", extra={"user_id": user_id})
            raise
        finally:
            sse_manager.unsubscribe_user(user_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent buffering in proxies
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
