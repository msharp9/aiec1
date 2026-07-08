# 🐾 Whiskers — the Cat Health Assistant

A chat web app for **Whiskerful Wonders Cat Café**. Customers type a question about
their cat and get friendly, grounded guidance from *Whiskers*, an agent built on the
**Claude Agent SDK** — and scaffolded entirely with **Claude Code**.

Built to the spec in [`../email.txt`](../email.txt).

## What it does

- 💬 **Chat page** in the browser — no install.
- ⌨️ **Streams word by word** (Server-Sent Events) so it feels alive.
- 🧠 **Remembers the conversation** — each chat maps to its own SDK session, so
  "my cat is Biscuit" is still known when you later ask "is tuna okay for him?"
- 🔧 **Looks things up instead of guessing**, via two custom tools:
  - `check_vitals` — temperature / heart rate / breathing rate vs normal cat ranges.
  - `check_food_safety` — food & plant safety (safe / caution / toxic / emergency),
    with lilies, chocolate, grapes, etc. treated as emergencies.
- 🛡️ **Guardrails**: not a vet (says so), leads with *GO TO THE EMERGENCY VET* for
  red-flag symptoms, and politely stays cats-only.
- 🔒 **Locked down**: the agent's only abilities are those two tools — no file,
  shell, or web access — so it can't poke around the server or the internet.
- 😿 **No scary errors**: any failure becomes a polite "try again in a moment."
- 🗂️ **Multi-conversation sidebar**: start and switch between separate chats.

## Requirements

- Python 3.12+ and [`uv`](https://docs.astral.sh/uv/)
- Access to Claude via **AWS Bedrock** (this project) *or* an `ANTHROPIC_API_KEY`.
  On Bedrock, ensure `CLAUDE_CODE_USE_BEDROCK=1`, `AWS_REGION`, and valid AWS
  credentials (e.g. `AWS_PROFILE`) are in the environment — the SDK reads them; no
  API key needed. On the direct API instead, `export ANTHROPIC_API_KEY=sk-ant-...`.

## Run

```bash
uv sync                                 # install deps
uv run uvicorn app:app --reload         # serve on http://localhost:8000
```

Open http://localhost:8000 and ask something like *"my cat ate chocolate, how bad
is it?"*

Optional: override the model with `WHISKERS_MODEL` (defaults to a Bedrock inference
profile), e.g. `WHISKERS_MODEL="us.anthropic.claude-opus-4-8[1m]" uv run uvicorn ...`.

## Quick test (no browser)

```bash
curl -s localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"can cats eat cheese?","conversation_id":"t1"}'
```

## How it fits together

```
browser (static/)  ──POST /api/chat[/stream]──▶  app.py (FastAPI)
                                                    │  calls the seam
                                                    ▼
                                            whiskers.py  ── query() ──▶  Claude (Bedrock)
                                                    │                         │
                                            whiskers_tools.py ◀── tool calls ─┘
                                            (check_vitals, check_food_safety)
```

- **`app.py`** — routes + the `conversation_id → session_id` memory map.
- **`whiskers.py`** — the agent: system prompt (persona + guardrails), the
  read-only tool allowlist, `max_turns`, streaming, and error handling. This is the
  swappable "brain" seam.
- **`whiskers_tools.py`** — the two in-process custom tools and their reference data.
- **`static/`** — plain HTML/CSS/JS UI: sidebar + streaming, no framework.

See [`CLAUDE.md`](./CLAUDE.md) for the constraints that must not be broken.
