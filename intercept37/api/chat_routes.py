"""FastAPI routes for the agentic chat system.

Exposes a streaming SSE endpoint so clients can interact with the Claude
agent in real time, plus session-management helpers.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from intercept37.agent.chat import AgentChat

logger = logging.getLogger("intercept37.api.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Shared agent instance — conversations persist in memory.
_agent = AgentChat()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

async def _event_stream(session_id: str, message: str):
    """Yield Server-Sent Events from the agentic chat loop."""
    try:
        async for event in _agent.chat(session_id, message):
            yield f"data: {json.dumps(event, default=str)}\n\n"
    except Exception as exc:
        logger.exception("Chat stream error")
        yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("")
async def chat(body: ChatRequest):
    """Send a message to the AI agent and receive a streamed SSE response.

    Each SSE `data:` line is a JSON object with a ``type`` field:
    - ``text`` — partial text from the model
    - ``tool_use`` — a tool is being invoked
    - ``tool_result`` — result of a tool invocation
    - ``done`` — turn complete
    - ``error`` — something went wrong
    """
    return StreamingResponse(
        _event_stream(body.session_id, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx compatibility
        },
    )


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session's conversation history."""
    _agent.clear_session(session_id)
    return {"status": "ok", "session_id": session_id}


@router.get("/sessions")
async def list_sessions():
    """List all active chat session IDs."""
    return {"sessions": _agent.get_sessions()}


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    """Get the raw message history for a session (for debugging)."""
    history = _agent.get_history(session_id)
    return {"session_id": session_id, "messages": len(history), "history": history}
