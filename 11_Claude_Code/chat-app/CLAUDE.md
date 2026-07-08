# Whiskers — Cat Health Assistant

Chat web app for Whiskerful Wonders Cat Café. A browser chat where an Agent-SDK
agent ("Whiskers") answers cat-health questions. Product spec: `../email.txt`.

## Run & test

```bash
uv run uvicorn app:app --reload        # http://localhost:8000
```

Auth is via AWS Bedrock (this machine has CLAUDE_CODE_USE_BEDROCK=1 + AWS_PROFILE);
the SDK inherits it — no ANTHROPIC_API_KEY. Override the model with `WHISKERS_MODEL`.

```bash
# non-streaming smoke test
curl -s localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"can cats eat cheese?","conversation_id":"t1"}'
```

## The seam (the one architecture fact that matters)

The web layer never talks to the model. `app.py` calls into `whiskers.py`
(`stream_whiskers` / `run_whiskers`) — that's the swappable brain. To change the
agent, change `whiskers.py`; `app.py` stays put.

## Non-negotiable constraints (from email.txt)

- **Allowlist is the safety gate.** Whiskers' ONLY tools are the two in
  `whiskers_tools.py` (`check_vitals`, `check_food_safety`), allowlisted as
  `mcp__whiskers__*`. No Read/Glob/Grep/Bash/Web, no `cwd`. Do not add file/shell
  tools — the customer explicitly forbade server/internet access.
- **Guardrails live in `SYSTEM_PROMPT`** (whiskers.py): not-a-vet disclaimer,
  emergency-vet-first for red-flag symptoms, cats-only redirect. Edit them there.
- **Never surface a raw error.** Failures return `ERROR_REPLY` (a polite chat
  message), never a 500.
- Frontend is plain HTML/CSS/JS in `static/` — no framework.

## Layout

- `app.py` — FastAPI: `/`, `/api/chat`, `/api/chat/stream` (SSE); `SESSIONS` maps
  `conversation_id → session_id` for per-conversation memory.
- `whiskers.py` — the agent: options, system prompt, streaming loop, error handling.
- `whiskers_tools.py` — the two custom tools + reference data.
- `static/` — chat UI with conversation sidebar and word-by-word streaming.
