import re
import time
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agent import AgentResult, run_agent
from database import AsyncSessionLocal, get_db, init_db
from logger import log_decision, new_request_id, set_request_id, setup_logger
from models import ChatTrace, Customer, Decision, RefundLog, RefundRequest, RefundStatus
from pricing import calculate_cost
from security import check_injection
from seed import seed_data
from tools import get_customer_order_data


class ChatHistoryMessage(BaseModel):
    role: str
    text: str
    decision: str | None = None


class ChatRequest(BaseModel):
    customer_id: str
    message: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    decision: str | None
    reason: str
    escalated: bool
    policy_rule: str | None


class TraceResponse(BaseModel):
    id: str
    timestamp: str
    customer_id: str
    customer_name: str
    user_message: str
    agent_response: str
    decision: str
    policy_rule: str | None
    model_used: str | None
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    status: str


BUSY_SUPPORT_MESSAGE = "Our favourite support agent seems busy. We'll connect you to someone else in a moment."
limiter = Limiter(key_func=get_remote_address)


def _normalize_customer_code(value: str) -> str:
    normalized = value.strip().upper()
    if re.fullmatch(r"C[O0]{2}\d", normalized):
        return f"C00{normalized[-1]}"
    return normalized


def _message_customer_id(message: str) -> str | None:
    match = re.search(r"\bC[O0]{2}\d\b", message, flags=re.IGNORECASE)
    return _normalize_customer_code(match.group(0)) if match else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_data(session)
    yield


app = FastAPI(title="Hrishikesh's Refund Agent", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = new_request_id()
    set_request_id(request_id)
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    log_decision(path=request.url.path, method=request.method, status_code=response.status_code, latency_ms=int((time.perf_counter() - start) * 1000))
    return response


async def _save_refund_log(
    session: AsyncSession,
    customer_id: str,
    message: str,
    result: AgentResult,
    request_id: str,
) -> None:
    order = result.order_details
    if not order.get("found"):
        return
    refund_request = RefundRequest(
        id=uuid.uuid4(),
        order_id=uuid.UUID(str(order["order_id"])),
        order_item_id=uuid.UUID(str(order["order_item_id"])),
        customer_id=uuid.UUID(str(order["customer_id"])),
        reason=message,
        amount_requested=Decimal(str(order["total_amount"])),
        status=RefundStatus(result.decision),
    )
    session.add(refund_request)
    await session.flush()
    session.add(
        RefundLog(
            refund_request_id=refund_request.id,
            agent_request_id=request_id,
            decision=Decision(result.decision),
            policy_rule=result.policy_rule,
            reason=result.reason,
            agent_latency_ms=result.latency_ms,
            model_used=result.model_used,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=Decimal(str(round(result.cost_usd, 8))),
        )
    )
    await session.commit()
    log_decision(
        customer_id=customer_id,
        decision=result.decision,
        latency_ms=result.latency_ms,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
    )


async def _save_chat_trace(
    session: AsyncSession,
    customer_id: str,
    message: str,
    result: AgentResult,
    request_id: str,
) -> None:
    order = result.order_details or {}
    stored_customer_id = None
    customer_label = customer_id
    if order.get("found"):
        stored_customer_id = uuid.UUID(str(order["customer_id"]))
        customer_label = str(order.get("customer_name") or customer_id)
    else:
        normalized = _normalize_customer_code(customer_id)
        customer = await session.scalar(
            select(Customer).where(Customer.email.ilike(f"{normalized.lower()}@%"))
        )
        if customer:
            stored_customer_id = customer.id
            customer_label = customer.full_name

    session.add(
        ChatTrace(
            id=uuid.uuid4(),
            request_id=request_id,
            customer_id=stored_customer_id,
            customer_label=customer_label,
            user_message=message,
            agent_response=result.reason,
            decision=None if result.decision == "none" else result.decision,
            policy_rule=result.policy_rule,
            escalated=result.escalated,
            model_used=result.model_used,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=Decimal(str(round(result.cost_usd, 8))),
            latency_ms=result.latency_ms,
        )
    )
    await session.commit()


async def _chat_response(
    session: AsyncSession,
    customer_id: str,
    message: str,
    result: AgentResult,
    request_id: str,
) -> ChatResponse:
    if result.decision not in ("none", None):
        await _save_refund_log(session, customer_id, message, result, request_id)
    await _save_chat_trace(session, customer_id, message, result, request_id)
    return ChatResponse(
        decision=result.decision,
        reason=result.reason,
        escalated=result.escalated,
        policy_rule=result.policy_rule,
    )


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(payload: ChatRequest, request: Request, session: AsyncSession = Depends(get_db)):
    injection = check_injection(payload.message)
    request_id = request.state.request_id
    effective_customer_id = _message_customer_id(payload.message) or _normalize_customer_code(payload.customer_id)

    if injection["flagged"]:
        order = await get_customer_order_data(effective_customer_id)
        result = AgentResult(
            decision="denied",
            reason="Security: prompt injection detected",
            policy_rule=f"security_injection:{injection['pattern']}",
            escalated=False,
            model_used="security-filter",
            order_details=order,
        )
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id)

    try:
        result = await run_agent(
            effective_customer_id,
            payload.message,
            request_id,
            [item.model_dump() for item in payload.history],
        )
    except Exception:
        order = await get_customer_order_data(effective_customer_id)
        result = AgentResult(
            decision="escalated",
            reason=BUSY_SUPPORT_MESSAGE,
            policy_rule="llm_unavailable",
            escalated=True,
            model_used="unavailable",
            order_details=order,
        )

    return await _chat_response(session, effective_customer_id, payload.message, result, request_id)


@app.get("/api/traces", response_model=list[TraceResponse])
async def traces(session: AsyncSession = Depends(get_db)):
    stmt = (
        select(ChatTrace)
        .order_by(desc(ChatTrace.created_at))
        .limit(50)
    )
    rows = (await session.execute(stmt)).scalars().all()
    response = []
    for trace in rows:
        cost = calculate_cost(trace.prompt_tokens, trace.completion_tokens, trace.model_used) if not trace.cost_usd else float(trace.cost_usd)
        response.append(
            TraceResponse(
                id=str(trace.id),
                timestamp=trace.created_at.isoformat(),
                customer_id=str(trace.customer_id or ""),
                customer_name=trace.customer_label,
                user_message=trace.user_message,
                agent_response=trace.agent_response,
                decision=trace.decision or "none",
                policy_rule=trace.policy_rule,
                model_used=trace.model_used,
                prompt_tokens=trace.prompt_tokens,
                completion_tokens=trace.completion_tokens,
                cost_usd=cost,
                latency_ms=trace.latency_ms,
                status="escalated" if trace.escalated else "answered",
            )
        )
    return response


@app.get("/health")
async def health(session: AsyncSession = Depends(get_db)):
    db_ok = False
    llm_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    try:
        client = AsyncOpenAI()
        await client.models.list()
        llm_ok = True
    except Exception:
        llm_ok = False
    return {"status": "ok" if db_ok and llm_ok else "degraded", "db": db_ok, "llm": llm_ok}
