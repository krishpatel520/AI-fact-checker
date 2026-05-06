"""
ws.py
-----
FastAPI WebSocket endpoint for real-time analysis results.

When a client submits an analysis job it can subscribe to
  ws://<host>/ws/{job_id}
and receive a single JSON push when the AggregatorAgent finishes.

The implementation uses Redis async pub/sub:
  - AggregatorAgent publishes to the channel "job:{job_id}"
  - This endpoint subscribes and relays the message to the browser
  - After one message the connection closes (analysis is a one-shot event)

Falls back gracefully if the client disconnects before the result arrives.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WS_TIMEOUT_SECONDS = int(os.getenv("WS_TIMEOUT_SECONDS", "180"))

router = APIRouter()


@router.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Subscribe to analysis results for a given job_id.

    The client connects, waits, and receives exactly one message:
      {"job_id": "...", "status_event": "done", ...full analysis payload...}
    or a timeout message if the job takes too long.
    """
    await websocket.accept()
    logger.info("WS client connected for job %s", job_id)

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"job:{job_id}")

    try:
        async def _listen():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    return message["data"]
            return None

        data = await asyncio.wait_for(_listen(), timeout=WS_TIMEOUT_SECONDS)

        if data:
            await websocket.send_text(data)
        else:
            await websocket.send_text(
                json.dumps({"status_event": "error", "detail": "No result received."})
            )

    except asyncio.TimeoutError:
        logger.warning("WS timeout for job %s after %ds", job_id, WS_TIMEOUT_SECONDS)
        await websocket.send_text(
            json.dumps({
                "status_event": "timeout",
                "detail": f"Analysis exceeded {WS_TIMEOUT_SECONDS}s. Poll /api/job/{job_id} for result.",
            })
        )

    except WebSocketDisconnect:
        logger.info("WS client disconnected for job %s", job_id)

    finally:
        await pubsub.unsubscribe(f"job:{job_id}")
        await r.aclose()
        try:
            await websocket.close()
        except Exception:
            pass
