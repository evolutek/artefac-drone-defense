"""
Simple in-process event bus for broadcasting backend events to multiple subscribers.
Used by the gRPC server to stream real-time events to clients.
"""
import asyncio
from typing import Any, Dict, Set

_subscribers: Set[asyncio.Queue] = set()

def subscribe() -> asyncio.Queue:
    """Create a new subscription queue for events."""
    q: asyncio.Queue = asyncio.Queue(maxsize=256)
    _subscribers.add(q)
    return q

async def unsubscribe(q: asyncio.Queue):
    """Remove a subscription queue."""
    if q in _subscribers:
        _subscribers.remove(q)

def publish(event: Dict[str, Any]):
    """Publish an event to all subscriber queues.

    The event should be a dict like:
      {"type": "state", "drone_id": "system", "data": {"type": "product_delete", ...}}
    """
    dead: Set[asyncio.Queue] = set()
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            # Drop subscriber if it cannot keep up
            dead.add(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except KeyError:
            pass

