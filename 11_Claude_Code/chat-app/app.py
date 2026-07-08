"""FastAPI backend for Whiskers, the Cat Health Assistant.

Routes:
  GET  /                  -> static/index.html (the chat UI)
  POST /api/chat          -> {message, conversation_id} => {reply, conversation_id}
                             (non-streaming; kept as the simple, testable seam)
  POST /api/chat/stream   -> Server-Sent Events: word-by-word reply + tool activity

Conversation memory (README Task 7): each browser conversation_id is mapped to an
SDK session_id so follow-up messages resume the same agent session. In-memory is
fine for the café's needs today.
"""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from whiskers import ERROR_REPLY, run_whiskers, stream_whiskers

app = FastAPI(title="Whiskers — Cat Health Assistant")

STATIC_DIR = Path(__file__).parent / "static"

# conversation_id (browser) -> session_id (SDK). In-memory; resets on restart.
SESSIONS: dict[str, str] = {}


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def _resolve_conversation(conversation_id: str | None) -> tuple[str, str | None]:
    """Return (conversation_id, resume_session_id), minting an id if none was sent."""
    conversation_id = conversation_id or uuid.uuid4().hex
    return conversation_id, SESSIONS.get(conversation_id)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Non-streaming chat. Simple to curl; always returns a polite reply, never a 500."""
    conversation_id, resume = _resolve_conversation(req.conversation_id)
    reply, session_id = await run_whiskers(req.message, resume=resume)
    if session_id:
        SESSIONS[conversation_id] = session_id
    return JSONResponse({"reply": reply, "conversation_id": conversation_id})


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """Streaming chat over SSE: 'tool', 'delta', and terminal 'final'/'error' events."""
    conversation_id, resume = _resolve_conversation(req.conversation_id)

    async def event_source():
        try:
            async for event in stream_whiskers(req.message, resume=resume):
                if event.session_id:
                    SESSIONS[conversation_id] = event.session_id
                payload = {"type": event.type, "text": event.text,
                           "conversation_id": conversation_id}
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception:  # noqa: BLE001 — even a transport failure stays polite
            payload = {"type": "error", "text": ERROR_REPLY,
                       "conversation_id": conversation_id}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# Serve remaining assets (app.js, style.css) under /static.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
