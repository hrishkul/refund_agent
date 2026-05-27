# Hrishikesh's Refund Agent

## About
Hrishikesh's Refund Agent is a fully containerized AI refund workflow that combines deterministic policy enforcement, GPT-4o reasoning, human escalation, PostgreSQL audit logs, and self-hosted Langfuse observability for production-style e-commerce refund decisions.

## Setup
```bash
cp .env.example .env
# Add your OPENAI_API_KEY
docker-compose up
```

## Access
- Customer chat UI: http://localhost
- Admin dashboard: http://localhost/admin
- Langfuse observability: http://localhost:3000
- Langfuse login: `admin@worknoon.local` / `worknoon-admin`

## Architecture
The React + Vite frontend serves customer chat and an operations dashboard through Nginx. FastAPI exposes the chat, trace, and health APIs. PostgreSQL 16 stores customers, orders, refund requests, Langfuse tables, and agent logs. LangGraph runs the refund agent tool loop with OpenAI GPT-4o, while Langfuse captures traces in the self-hosted container.

## Agent Loop
Requests pass through prompt-injection screening before any model call. Safe requests require `OPENAI_API_KEY`; without it, the API escalates with a support handoff message instead of guessing a policy outcome. With an API key, requests enter a LangGraph StateGraph that calls `get_customer_order`, evaluates `check_refund_policy`, validates the structured Pydantic decision, calculates token cost from Langfuse's models endpoint, and writes the refund request plus audit log.

The agent enforces two complementary layers of policy:
1. **Deterministic engine** (`tools.py` → `check_refund_policy_data`) — rule-by-rule evaluation with no LLM involvement, applied at confirmation time.
2. **LLM reasoning layer** (`agent.py` → LangGraph) — GPT-4o reads the full policy document and produces a structured `AgentDecision` with a customer-facing explanation.

> For a full architectural walkthrough, see [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md).

## Edge Cases Handled

| Customer | Scenario | Policy Rule | Expected Outcome |
| --- | --- | --- | --- |
| C001 | Normal eligible refund within 30 days, delivered order | Rule 2 | Approved |
| C002 | Final sale product | Rule 1 | Denied — no exceptions |
| C003 | Refund requested on day 35 | Rule 2 | Denied — outside return window |
| C004 | Order total over $500 | Rule 3 | Escalated to human agent |
| C005 | Digital product already downloaded | Rule 5 | Denied |
| C006 | Defective item within 60 days | Rule 4 | Approved |
| C007 | Shipped but not delivered | Rule 6 | Denied — must wait for delivery |
| C008 | Premium customer requesting on day 40 | Rule 2 (Premium) | Approved — 45-day window |
| C009 | Order still pending shipment | Rule 6 | Approved — cancellation refund |
| C010 | Order in processing state | Rule 6 | Approved — cancellation refund |
| C011 | Gift order — store credit scenario | Rule 7 | Approved — store credit only |
| C012 | Holiday order (Nov–Dec purchase) within Jan 31 | Rule 8 | Approved — holiday extended window |
| C013 | Holiday order but expired past Jan 31 | Rule 8 + Rule 2 | Denied — all windows expired |
| C014 | Multi-unit order, partial return | Rule 9 | Partial refund per unit |
| C015 | Late Premium customer, day 70 | Rule 2 | Denied — outside 45-day window |

## Two-Layer Injection Defense
Prompt injection is blocked at two independent layers:
1. **Keyword filter** (`security.py`) — 10 known injection patterns ("ignore previous", "bypass", "act as", etc.) are screened before any LLM call.
2. **System prompt hardening** (`agent.py`) — the LLM-level instruction explicitly instructs Maya to ignore policy override attempts regardless of phrasing.

## Observability with Langfuse
Langfuse runs locally through Docker Compose and is initialized with `LANGFUSE_INIT_*` environment variables. The backend receives the same local project API keys, so `@observe()` traces are sent to the `worknoon-refund-agent` Langfuse project and correlate with the backend `request_id`, model, token, latency, cost, decision, and policy rule fields.

## Relevance to Hrishikesh's Refund Agent
The same architecture maps cleanly to booking dispute resolution: fetch booking and user context, run deterministic policy tools for cancellation, refunds, and escalation thresholds, then let the agent explain the decision while every action remains auditable through trace logs and cost telemetry.
