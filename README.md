# WhatsApp Business Agentic AI Framework

An extensible, multi-client Python framework that enables companies to serve
customers via WhatsApp Business chat using an agentic AI architecture.

## Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) package manager

## 1. Install Dependencies

```bash
uv sync
```

This installs FastAPI, SQLAlchemy, uvicorn, httpx, aiosmtplib, pytest, and all
other required packages into a local `.venv`.

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials. Key variables:

| Variable | Description | Required for |
|----------|-------------|-------------|
| `DATABASE_URL` | SQLAlchemy connection string | Always (defaults to SQLite) |
| `WHATSAPP_API_TOKEN` | Meta Cloud API Bearer token | Sending real WhatsApp replies |
| `WHATSAPP_PHONE_NUMBER_ID` | Your WhatsApp Business phone ID | Sending real WhatsApp replies |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification secret | Webhook setup with Meta |
| `SMTP_HOST`, `SMTP_PORT` | Mail server | Sending confirmation emails |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Mail credentials | Sending confirmation emails |
| `EMAIL_FROM` | Sender address | Sending confirmation emails |

> **Note:** The simulator and tests work fine without any of the WhatsApp or SMTP
> variables configured.

## 3. Seed the Database

Populates the database with 4 sample users across 2 companies (`acme_corp` and
`globex_inc`):

```bash
PYTHONPATH=src uv run python seed.py
```

**Sample users created:**

| Name | Company | Client Code | Phone |
|------|---------|-------------|-------|
| Alice Johnson | acme_corp | ACME-1001 | +15551234567 |
| Bob Smith | acme_corp | ACME-1002 | +15559876543 |
| Carol Davis | globex_inc | GLX-2001 | +442071234567 |
| Dan Wilson | globex_inc | GLX-2002 | +919876543210 |

## 4. Run the Chat Simulator

The easiest way to test — an interactive CLI that routes messages through the
real framework without needing WhatsApp:

```bash
PYTHONPATH=src uv run python simulator.py
```

**Simulator commands:**

| Command | Action |
|---------|--------|
| *(any text)* | Send a message to the agent |
| `switch` | Change the simulated phone number |
| `logout` | Clear your session and start over |
| `quit` | Exit the simulator |

**Try these scenarios:**

```
Phone: +15551234567  →  type anything  →  instant verification (known phone)
Phone: +19999999999  →  type anything  →  asks for Client ID  →  type GLX-2001  →  verified
Phone: +19999999999  →  type anything  →  asks for Client ID  →  type INVALID   →  not found
```

## 5. Start the Development Server

Runs the full FastAPI server with live reload:

```bash
PYTHONPATH=src uv run uvicorn whatsapp_agent.main:app --reload --host 0.0.0.0 --port 8000
```

**Available endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/webhook` | WhatsApp verification challenge |
| POST | `/webhook` | Receive incoming WhatsApp messages |
| GET | `/docs` | Interactive Swagger UI |

## 6. Test with cURL

With the server running, you can simulate WhatsApp webhook payloads:

**Known phone (instant auth):**
```bash
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"+15551234567","text":{"body":"Hi"}}]}}]}]}'
```

**Unknown phone (triggers Client ID prompt):**
```bash
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"+19999999999","text":{"body":"Hello"}}]}}]}]}'
```

**Send Client ID (follow-up from unknown phone):**
```bash
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"+19999999999","text":{"body":"GLX-2001"}}]}}]}]}'
```

> Watch the server terminal for agent reply logs (replies are logged when
> `WHATSAPP_API_TOKEN` is not set).

## 7. Run Tests

```bash
uv run pytest tests/ -v
```

**Test coverage:**

| Test | What it verifies |
|------|-----------------|
| `test_phone_match` | Known phone → instant verification |
| `test_client_id_fallback` | Unknown phone → Client ID → verified + email sent |
| `test_no_match` | Unknown phone + invalid Client ID → rejection |
| `test_already_authenticated` | Re-message after auth → still verified |
| `test_find_by_phone_match` | DB lookup by phone returns correct user |
| `test_find_by_phone_no_match` | DB lookup by unknown phone returns None |
| `test_find_by_client_code_match` | DB lookup by client code returns correct user |
| `test_find_by_client_code_no_match` | DB lookup by unknown code returns None |

## Architecture

```
src/whatsapp_agent/
├── main.py              # FastAPI entry point
├── config.py            # Pydantic Settings (.env loader)
├── models/user.py       # SQLAlchemy User model
├── database/
│   ├── engine.py        # Async DB engine & session factory
│   └── repository.py    # UserRepository (queries)
├── agents/
│   ├── base.py          # BaseAgent abstract class
│   └── auth_agent.py    # Authentication agent
├── services/
│   ├── email_service.py     # SMTP email sender
│   ├── session_manager.py   # Per-user session state
│   └── message_router.py    # Routes messages to agents
└── webhook/
    └── handler.py       # WhatsApp webhook endpoints
```

## Authentication Flow

1. User sends a message on WhatsApp
2. Framework looks up the sender's phone number in the database
3. If found → user is verified immediately
4. If not found → user is asked for their Client ID
5. If Client ID matches → confirmation email is sent, user is verified
6. If neither matches → user is directed to support

## Adding New Agents

Create a new class inheriting from `BaseAgent`:

```python
from whatsapp_agent.agents.base import AgentResponse, BaseAgent

class MyTaskAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "MyTaskAgent"

    async def handle(self, message: str, session_state: dict) -> AgentResponse:
        # Your logic here
        return AgentResponse(reply_text="Done!")
```

Then register it in `message_router.py`.

