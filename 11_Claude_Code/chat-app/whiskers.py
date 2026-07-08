"""Whiskers, the Cat Health Assistant — the agent behind the chat app.

This module is the SEAM the whole project is built around. The chat backend
(app.py) never talks to the model directly; it calls run_whiskers() here. Swap
the body of run_whiskers() and you swap the brain — the web layer never changes.

Whiskers is deliberately locked down (email.txt #5): its ONLY abilities are the
two custom tools in whiskers_tools.py. No file, shell, search, or web tools, and
no cwd — so it structurally cannot poke around the server or the internet, no
matter what a customer types.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from whiskers_tools import WHISKERS_TOOL_NAMES, whiskers_server

# Load auth/config from a local .env if present (see .env.example). This makes the
# server self-contained: it doesn't depend on which env vars happen to be exported
# in the shell that launched uvicorn. Real values here (never commit .env).
load_dotenv(Path(__file__).parent / ".env")

# Model: on Bedrock the SDK reads CLAUDE_CODE_USE_BEDROCK / AWS_* from the env.
# Allow an override via env, else fall back to the Bedrock inference profile.
MODEL = os.environ.get("WHISKERS_MODEL", "us.anthropic.claude-sonnet-4-6[1m]")

# Auth env the spawned CLI needs. We forward these explicitly via options.env so
# the agent authenticates the same way regardless of the parent shell — and so it
# still works even though setting_sources=[] tells the CLI to ignore ~/.claude.
_AUTH_ENV_KEYS = (
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
    "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_PROFILE",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
)
_AUTH_ENV = {k: os.environ[k] for k in _AUTH_ENV_KEYS if os.environ.get(k)}

SYSTEM_PROMPT = """\
You are Whiskers, the friendly cat health assistant for Whiskerful Wonders Cat Café.
You help worried cat parents with general, everyday cat-care questions in a warm,
reassuring, lightly playful tone.

HARD RULES — follow every time:

1. You are NOT a veterinarian. Give general guidance only. For anything serious,
   ongoing, or uncertain, tell the customer to call their own veterinarian. Include
   a brief "I'm not a vet" disclaimer when giving health guidance.

2. EMERGENCIES COME FIRST. If the message describes a red-flag symptom — trouble
   breathing, can't urinate, collapsed, seizing, ate a lily or other toxic item,
   ongoing bleeding, ingested poison — your VERY FIRST line must be, in bold:
   "🚨 GO TO THE EMERGENCY VET NOW." Then briefly explain why. Do not bury this
   under other text.

3. CATS ONLY. If someone asks about another animal (dog, iguana, etc.) or anything
   not cat-related (crypto, weather...), politely and briefly steer them back to
   cats. Do not answer the off-topic question.

4. USE YOUR TOOLS — don't guess:
   - When the customer gives vital-sign numbers (temperature, heart rate, breathing
     rate), call check_vitals to compare against normal feline ranges.
   - When the customer asks whether a food or plant is okay for a cat, call
     check_food_safety. Treat "emergency" results as true emergencies (rule 2).
   If a food isn't in the database, say you don't have a confirmed answer rather
   than guessing.

Keep answers concise and easy to read for an anxious person on their phone.\
"""


def _build_options(resume: str | None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=MODEL,
        mcp_servers={"whiskers": whiskers_server},
        # The allowlist IS the safety gate on a headless server (email.txt #5,
        # README Question #4). Exactly the two custom tools; nothing else.
        allowed_tools=WHISKERS_TOOL_NAMES,
        setting_sources=[],       # ignore the host machine's personal ~/.claude config
        env=_AUTH_ENV,            # forward auth (Bedrock/Vertex/API key) explicitly
        max_turns=25,             # hard cap so no request can loop forever
        resume=resume,            # continue this conversation's session if we have one
        include_partial_messages=True,  # emit StreamEvents for word-by-word streaming
    )


# Polite, on-brand fallback for any failure (email.txt #6) — never a 500.
ERROR_REPLY = (
    "😿 Sorry, I had a little hiccup just now — please try again in a moment. "
    "And if it's urgent, please call your veterinarian right away."
)


def _log_error(detail: str) -> None:
    """Log the real failure reason to the server console (never shown to customers)."""
    print(f"[whiskers] agent error: {detail}")
    low = detail.lower()
    if "not logged in" in low or "/login" in low or "api" in low and "key" in low:
        print(
            "[whiskers] AUTH not configured. The agent process could not authenticate.\n"
            "           On Bedrock: export CLAUDE_CODE_USE_BEDROCK=1, AWS_REGION, and valid\n"
            "           AWS creds (AWS_PROFILE=...) in the shell that runs uvicorn, or put\n"
            "           them in chat-app/.env (see .env.example). On the direct API instead:\n"
            "           export ANTHROPIC_API_KEY=sk-ant-..."
        )


@dataclass
class WhiskersEvent:
    """One thing that happened while Whiskers worked, for the UI to render."""
    type: str            # "session" | "tool" | "delta" | "final" | "error"
    text: str = ""       # delta text, final reply, or tool label
    session_id: str = ""  # set on "session" and "final" events


async def stream_whiskers(
    message: str, resume: str | None = None
) -> AsyncIterator[WhiskersEvent]:
    """Run Whiskers and yield events as they happen (for streaming to the browser).

    Yields WhiskersEvents: a "session" event with the session_id, "tool" events as
    tools fire, "delta" events with text chunks, and one terminal "final" (with the
    full reply + session_id) or "error" event.
    """
    session_id = resume or ""
    final_text = ""
    error_detail: str | None = None  # the real diagnostic, for the server log only
    try:
        async for msg in query(prompt=message, options=_build_options(resume)):
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                session_id = msg.data.get("session_id", session_id)
                yield WhiskersEvent(type="session", session_id=session_id)

            elif isinstance(msg, StreamEvent):
                event = msg.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield WhiskersEvent(type="delta", text=delta["text"])

            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    # Only surface Whiskers' own tools to the UI (ignore any host
                    # environment meta-tools). These are the only ones allowlisted anyway.
                    if isinstance(block, ToolUseBlock) and block.name.startswith("mcp__whiskers__"):
                        label = block.name.split("__")[-1]  # mcp__whiskers__check_vitals -> check_vitals
                        yield WhiskersEvent(type="tool", text=label)
                    elif isinstance(block, TextBlock):
                        final_text = block.text  # last text block = the answer

            elif isinstance(msg, ResultMessage):
                # An error result (auth failure, max_turns, throttling…) carries the
                # real reason in .result/.errors. The SDK then raises a bare
                # ProcessError, so grab the diagnostic HERE while we still have it.
                if msg.is_error:
                    error_detail = (msg.result or "; ".join(msg.errors or [])
                                    or msg.subtype or "unknown error")
                else:
                    final_text = (msg.result or final_text or "").strip()

        if error_detail:
            _log_error(error_detail)
            yield WhiskersEvent(type="error", text=ERROR_REPLY, session_id=session_id)
        else:
            yield WhiskersEvent(type="final", text=final_text or ERROR_REPLY,
                                session_id=session_id)

    except Exception as exc:  # noqa: BLE001 — any failure becomes a polite reply
        # Prefer the structured result reason over the SDK's opaque wrapper.
        _log_error(error_detail or f"{type(exc).__name__}: {exc}")
        yield WhiskersEvent(type="error", text=ERROR_REPLY, session_id=session_id)


async def run_whiskers(message: str, resume: str | None = None) -> tuple[str, str]:
    """Non-streaming convenience wrapper: returns (reply_text, session_id)."""
    reply, session_id = ERROR_REPLY, resume or ""
    async for event in stream_whiskers(message, resume):
        if event.type in ("final", "error"):
            reply, session_id = event.text, event.session_id or session_id
    return reply, session_id
