# Refund Agent

A fully containerised AI customer support agent that processes e-commerce refund requests using GPT-4o, deterministic policy enforcement, and a self-hosted Langfuse observability stack.

## Quick Start

```bash
cp .env.example .env
# Open .env and set OPENAI_API_KEY=sk-...
docker-compose up --build
```

> **First-run startup time:** Langfuse runs its database migrations on boot, which takes **60–120 seconds** on a cold machine. The backend waits for Langfuse to pass its health check before starting, so the total startup time before the UI is ready is typically **2–3 minutes**. Subsequent starts (with an existing volume) are under 30 seconds.

Once all containers are healthy:

| URL | Description |
| --- | --- |
| http://localhost | Customer chat UI |
| http://localhost/admin | Admin operations dashboard |
| http://localhost:3000 | Langfuse observability (self-hosted) |

Langfuse login: `admin@worknoon.local` / `worknoon-admin`

> **No API key?** The app starts and responds gracefully without `OPENAI_API_KEY` — every request is escalated to a human agent with a support handoff message instead of making a policy decision. Set the key to enable full LLM reasoning.

## Architecture

```
Browser
  └─ Nginx (port 80)
       ├─ /          → React + Vite frontend (static)
       ├─ /chat      → FastAPI backend (port 8000)
       ├─ /api/      → FastAPI backend
       └─ /health    → FastAPI backend

FastAPI
  ├─ Prompt injection screening (security.py)
  ├─ OpenAI Agents SDK runner (agent.py)
  │    ├─ get_customer_order   — queries PostgreSQL
  │    ├─ check_refund_policy  — deterministic 9-rule engine
  │    └─ get_refund_policy    — reads policy.txt
  ├─ Structured output → AgentDecision (Pydantic)
  ├─ Cost calculation (pricing.py)
  ├─ Refund log + ChatTrace written to PostgreSQL
  └─ @observe() trace sent to Langfuse

PostgreSQL 16
  ├─ customers, orders, order_items, products  (seeded on boot)
  ├─ refund_requests, refund_logs
  ├─ chat_traces                               (admin dashboard source)
  └─ Langfuse internal tables

Langfuse (self-hosted)
  └─ Full LLM trace capture with token, cost, latency, and metadata
```

## Agent Loop

Every `/chat` request goes through five stages:

1. **Injection screening** — `security.py` matches 10 known prompt-injection patterns and short-circuits to a denied response before any LLM call.
2. **Context assembly** — conversation history (last 8 turns) and customer ID are prepended to the user message.
3. **Agents SDK runner** — `Runner.run()` executes Maya (GPT-4o) with up to 10 turns. Maya calls tools in order: `get_customer_order` → `check_refund_policy` → optionally `get_refund_policy`.
4. **Structured decision** — the runner enforces a Pydantic `AgentDecision` output (`approved / denied / escalated / none`) with a customer-facing reason and the triggering policy rule.
5. **Persistence** — the decision, token usage, cost, latency, and tool call trace are written to `refund_logs` and `chat_traces`. An `@observe()` span is flushed to Langfuse.

## Two-Layer Policy Enforcement

| Layer | Where | What it does |
| --- | --- | --- |
| Deterministic engine | `tools.py → check_refund_policy_data()` | Evaluates all 9 rules without LLM involvement — no hallucination possible |
| LLM reasoning | `agent.py → SYSTEM_PROMPT` | GPT-4o reads the full policy text and produces a warm, customer-facing explanation |

The deterministic engine is the source of truth. The LLM layer adds explanation quality and handles conversational edge cases (greetings, follow-ups, injection attempts).

## Refund Policy Rules

| Rule | Condition | Outcome |
| --- | --- | --- |
| 1 | Final sale item | Denied — no exceptions |
| 2 | Outside 30-day window (45 days for premium) | Denied |
| 3 | Order total > $500 | Escalated to human agent |
| 4 | Defective item within 60 days | Approved |
| 5 | Digital product already downloaded | Denied |
| 6 | Order shipped but not delivered | Denied — must wait for delivery |
| 6 | Order pending/processing | Approved — cancellation refund |
| 7 | Gift order | Approved — store credit, not cash |
| 8 | Holiday order (Nov 15–Dec 31) returned by Jan 31 | Approved — extended window |
| 9 | Multi-unit order | Partial refund per unit returned |

## Test Scenarios (Seeded Customers)

| Customer | Scenario | Expected Outcome |
| --- | --- | --- |
| C001 | Normal eligible refund, delivered, within 30 days | Approved |
| C002 | Final sale product | Denied |
| C003 | Day 35, standard window | Denied |
| C004 | Order total > $500 | Escalated |
| C005 | Digital product already downloaded | Denied |
| C006 | Defective item within 60 days | Approved |
| C007 | Shipped but not yet delivered | Denied |
| C008 | Premium customer, day 40 | Approved (45-day window) |
| C009 | Order still pending shipment | Approved (cancellation) |
| C010 | Order in processing | Approved (cancellation) |
| C011 | Gift order | Approved — store credit only |
| C012 | Holiday order within Jan 31 | Approved — holiday window |
| C013 | Holiday order past Jan 31 | Denied — all windows expired |
| C014 | Multi-unit order, partial return | Partial refund per unit |
| C015 | Premium customer, day 70 | Denied — outside 45-day window |

## Cold Reset

To wipe all data and start completely fresh (e.g. after a schema change):

```bash
docker-compose down -v
docker-compose up --build
```

## Observability

Langfuse is provisioned automatically on first boot using `LANGFUSE_INIT_*` environment variables in `docker-compose.yml`. No manual Langfuse setup is required. Every agent run emits a trace to the `worknoon-refund-agent` project, correlated by `request_id`, with decision, policy rule, model, token counts, cost, and latency attached as metadata.

For a full architectural walkthrough, see [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md).
