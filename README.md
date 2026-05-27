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
Requests pass through prompt-injection screening before any model call. Safe requests require `OPENAI_API_KEY`; without it, the API escalates with a support handoff message instead of guessing a policy outcome. With an API key, requests enter a LangGraph StateGraph that calls `get_customer_order`, evaluates `check_refund_policy`, validates the structured Pydantic decision, calculates token cost from LiteLLM pricing JSON, and writes the refund request plus audit log.

## Edge Cases Handled
| Customer | Scenario | Expected outcome |
| --- | --- | --- |
| C001 | Normal eligible refund within 30 days, delivered order | Approved |
| C002 | Final sale product | Denied by policy rule 1 |
| C003 | Refund requested on day 35 | Denied by policy rule 2 |
| C004 | Order total over $500 | Escalated by policy rule 3 |
| C005 | Digital product already downloaded | Denied by policy rule 5 |
| C006 | Defective item within 60 days | Approved by policy rule 4 |
| C007 | Shipped but not delivered | Denied with return guidance by policy rule 6 |
| C008 | Premium customer requesting on day 40 | Approved by 45-day premium window |

## Observability with Langfuse
Langfuse runs locally through Docker Compose and is initialized with `LANGFUSE_INIT_*` environment variables. The backend receives the same local project API keys, so `@observe()` traces are sent to the `worknoon-refund-agent` Langfuse project and correlate with the backend `request_id`, model, token, latency, cost, decision, and policy rule fields.

## Relevance to Hrishikesh's Refund Agent
The same architecture maps cleanly to booking dispute resolution: fetch booking and user context, run deterministic policy tools for cancellation, refunds, and escalation thresholds, then let the agent explain the decision while every action remains auditable through trace logs and cost telemetry.
