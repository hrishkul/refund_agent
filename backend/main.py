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
from tools import check_refund_policy_data, get_customer_order_data, mark_latest_order_returned


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
OFF_TOPIC_MESSAGE = "I can help with ShopEase orders, refunds, returns, cancellations, exchanges, shipping, and policy questions. I can't help with unrelated topics."
limiter = Limiter(key_func=get_remote_address)


SHOP_TERMS = {
    "shopease",
    "order",
    "refund",
    "return",
    "cancel",
    "cancellation",
    "exchange",
    "replace",
    "replacement",
    "damaged",
    "defective",
    "broken",
    "shipping",
    "delivery",
    "delivered",
    "product",
    "item",
    "policy",
    "payment",
    "money",
    "chargeback",
    "escalate",
    "escalted",
    "escalated",
    "escalating",
    "escalation",
    "human",
    "agent",
    "support",
    "senior",
    "senior agent",
    "supervisor",
    "manager",
    "final sale",
    "take it back",
    "confirm",
    "confirmed",
    "yes",
}

OFF_TOPIC_TERMS = {
    "president",
    "prime minister",
    "capital of",
    "weather",
    "sports",
    "movie",
    "recipe",
    "stock price",
    "news",
    "election",
    "bike",
    "car",
    "honda",
}

GREETING_TERMS = {"hi", "hello", "hey", "thanks", "thank you"}
REFUND_TERMS = {"refund", "return", "cancel", "exchange", "replace", "take it back", "defective", "damaged", "broken"}


def _normalize_customer_code(value: str) -> str:
    normalized = value.strip().upper()
    if re.fullmatch(r"C[O0]{2}\d", normalized):
        return f"C00{normalized[-1]}"
    return normalized


def _message_customer_id(message: str) -> str | None:
    match = re.search(r"\bC[O0]{2}\d\b", message, flags=re.IGNORECASE)
    return _normalize_customer_code(match.group(0)) if match else None


def _is_customer_id_only(message: str) -> bool:
    return bool(re.fullmatch(r"\s*C[O0]{2}\d\s*", message, flags=re.IGNORECASE))


def _is_off_topic(message: str) -> bool:
    normalized = message.lower()
    if any(term in normalized for term in SHOP_TERMS):
        return False
    if normalized.strip() in GREETING_TERMS or normalized.startswith(("hi ", "hello ", "hey ")):
        return False
    if _is_customer_id_only(message):
        return False
    if any(term in normalized for term in OFF_TOPIC_TERMS):
        return True
    if normalized.startswith(("who is ", "what is ", "name ", "tell me about ", "explain ")) and "policy" not in normalized:
        return True
    return len(normalized.split()) > 1


def _wants_order_lookup(message: str) -> bool:
    normalized = message.lower()
    lookup_terms = ["show order", "show me order", "show orders", "my order", "order status", "list order"]
    return any(term in normalized for term in lookup_terms) and not any(term in normalized for term in REFUND_TERMS)


def _is_return_update(message: str) -> bool:
    normalized = message.lower()
    update_terms = [
        "i returned it",
        "i have returned it",
        "i already returned",
        "already returned it",
        "returned the product",
        "returned my product",
        "sent it back",
        "shipped it back",
        "mailed it back",
        "dropped it off",
    ]
    question_terms = ["did i", "have i", "has it", "is it", "?"]
    return any(term in normalized for term in update_terms) and not any(term in normalized for term in question_terms)


def _wants_return_status(message: str) -> bool:
    normalized = message.lower()
    status_terms = [
        "have i returned",
        "did i return",
        "has it been returned",
        "is it returned",
        "returned it already",
        "already returned",
    ]
    return any(term in normalized for term in status_terms)


async def _order_lookup_response(customer_id: str) -> AgentResult:
    order = await get_customer_order_data(customer_id)
    if not order.get("found"):
        return AgentResult(
            decision="none",
            reason="I couldn't find a recent ShopEase order for that customer ID. Please check the customer ID and try again.",
            model_used="order-lookup",
            order_details=order,
        )
    status = str(order.get("order_status", "unknown")).replace("_", " ")
    delivered = f" delivered {order['days_since_order']} days ago" if order.get("order_status") == "delivered" else f" currently marked {status}"
    return_status = " It is marked returned." if order.get("is_returned") else " It is not marked returned yet."
    reason = f"Hi {order.get('customer_name', 'there')}. Your latest order is {order.get('product_name', 'an item')}, total ${float(order.get('total_amount') or 0):.2f},{delivered}.{return_status}"
    return AgentResult(decision="none", reason=reason, model_used="order-lookup", order_details=order)


async def _return_update_response(customer_id: str) -> AgentResult:
    order = await mark_latest_order_returned(customer_id)
    if not order.get("found"):
        return AgentResult(
            decision="none",
            reason="I couldn't find a recent ShopEase order for that customer ID. Please check the customer ID and try again.",
            model_used="return-update",
            order_details=order,
        )
    returned_at = order.get("returned_at")
    reason = f"Thanks, {order.get('customer_name', 'there')}. I've marked {order.get('product_name', 'your item')} as returned in your order record."
    if returned_at:
        reason += " Maya will use that return status when checking your refund."
    return AgentResult(decision="none", reason=reason, model_used="return-update", order_details=order)


async def _return_status_response(customer_id: str) -> AgentResult:
    order = await get_customer_order_data(customer_id)
    if not order.get("found"):
        return AgentResult(
            decision="none",
            reason="I couldn't find a recent ShopEase order for that customer ID. Please check the customer ID and try again.",
            model_used="return-status",
            order_details=order,
        )
    if order.get("is_returned"):
        reason = f"Yes. {order.get('product_name', 'Your item')} is marked as returned in your ShopEase order record."
    else:
        reason = f"I don't see {order.get('product_name', 'your item')} marked as returned in your ShopEase order record yet."
    return AgentResult(decision="none", reason=reason, model_used="return-status", order_details=order)


def _latest_formal_decision(history: list[ChatHistoryMessage]) -> ChatHistoryMessage | None:
    for item in reversed(history):
        if item.role == "agent" and item.decision in {"approved", "denied", "escalated"}:
            return item
    return None


def _follow_up_response(message: str, history: list[ChatHistoryMessage]) -> AgentResult | None:
    previous = _latest_formal_decision(history)
    if not previous:
        return None
    normalized = message.lower()
    follow_up_terms = [
        "is it approved",
        "was it approved",
        "is my refund approved",
        "when will i get",
        "when do i get",
        "what happens next",
        "what does escalated mean",
        "why was it denied",
        "why denied",
        "what does that mean",
        "how long",
        "have i returned",
        "returned it already",
        "did i return",
        "already returned",
        "has it been returned",
    ]
    if not any(term in normalized for term in follow_up_terms):
        return None
    if previous.decision == "approved":
        reason = "Yes, your refund was approved. You should see it back on your original payment method within 5-7 business days."
    elif previous.decision == "denied":
        reason = previous.text if "sorry" in previous.text.lower() else f"That refund was denied. {previous.text}"
    else:
        reason = "Your return request has been escalated for senior review. I don't see a completed return confirmation here yet; a senior ShopEase agent will follow up within 24 hours."
    return AgentResult(decision="none", reason=reason, model_used="conversation-memory")


def _has_pending_approval(history: list[ChatHistoryMessage]) -> bool:
    for item in reversed(history):
        if item.role == "agent":
            text = item.text.lower()
            return "please reply confirm" in text and "refund" in text
    return False


def _is_confirmation(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized in {"confirm", "confirmed", "yes", "yes confirm", "i confirm", "please confirm", "go ahead", "approve it"}


def _is_decline(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized in {"decline", "cancel", "no", "no thanks", "do not", "don't", "stop", "never mind", "nevermind"}


def _has_refund_intent(message: str) -> bool:
    normalized = message.lower()
    return any(term in normalized for term in REFUND_TERMS)


def _approved_refund_response(message: str, history: list[ChatHistoryMessage]) -> AgentResult | None:
    previous = _latest_formal_decision(history)
    if not previous or previous.decision != "approved" or not _has_refund_intent(message):
        return None
    return AgentResult(
        decision="none",
        reason="This refund has already been approved in this conversation. You should see it back on your original payment method within 5-7 business days.",
        model_used="conversation-memory",
    )


async def _confirmed_refund_result(customer_id: str) -> AgentResult:
    order = await get_customer_order_data(customer_id)
    policy = check_refund_policy_data(order)
    recommendation = policy.get("recommendation", "denied")
    amount = float(order.get("total_amount") or 0)
    if recommendation == "approved" and amount > 0:
        reason = f"Confirmed. Your refund of ${amount:.2f} for {order.get('product_name', 'your order')} has been approved and should return to your original payment method within 5-7 business days."
        return AgentResult(
            decision="approved",
            reason=reason,
            policy_rule="eligible_standard_refund",
            escalated=False,
            model_used="policy-engine",
            order_details=order,
        )
    if recommendation == "approved":
        return AgentResult(
            decision="escalated",
            reason="I found the order is eligible, but I could not verify a valid refund amount. A senior ShopEase agent will review it within 24 hours.",
            policy_rule="missing_refund_amount",
            escalated=True,
            model_used="policy-engine",
            order_details=order,
        )
    return AgentResult(
        decision=recommendation,
        reason="I rechecked the order before confirming and it is no longer eligible for automatic approval. A ShopEase agent will review the details.",
        policy_rule=policy.get("rule_violated") or "policy_recheck_failed",
        escalated=recommendation == "escalated",
        model_used="policy-engine",
        order_details=order,
    )


async def _approval_confirmation_prompt(result: AgentResult, customer_id: str) -> AgentResult:
    order = result.order_details
    if not order.get("found") or float(order.get("total_amount") or 0) <= 0:
        order = await get_customer_order_data(customer_id)
    amount = float(order.get("total_amount") or 0)
    if amount <= 0:
        return AgentResult(
            decision="escalated",
            reason="This order appears eligible, but I could not verify a valid refund amount. A senior ShopEase agent will review it within 24 hours.",
            policy_rule="missing_refund_amount",
            escalated=True,
            model_used=result.model_used,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            order_details=order,
        )
    return AgentResult(
        decision="none",
        reason=f"{order.get('customer_name', 'Thanks')}, your refund of ${amount:.2f} for {order.get('product_name', 'your order')} is eligible. Please reply Confirm to issue it to your original payment method.",
        policy_rule=None,
        escalated=False,
        model_used=result.model_used,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
        order_details=order,
    )


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
    save_refund: bool = False,
) -> ChatResponse:
    if save_refund and result.decision != "none":
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
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id, save_refund=True)

    if _is_return_update(payload.message):
        result = await _return_update_response(effective_customer_id)
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id)

    if _wants_return_status(payload.message):
        result = await _return_status_response(effective_customer_id)
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id)

    if follow_up := _follow_up_response(payload.message, payload.history):
        return await _chat_response(session, effective_customer_id, payload.message, follow_up, request_id)

    if already_approved := _approved_refund_response(payload.message, payload.history):
        return await _chat_response(session, effective_customer_id, payload.message, already_approved, request_id)

    if _has_pending_approval(payload.history) and _is_decline(payload.message):
        result = AgentResult(
            decision="none",
            reason="No problem. I won't issue that refund. If you change your mind, you can ask me to check the return again.",
            escalated=False,
            model_used="conversation-memory",
            policy_rule=None,
        )
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id)

    if _has_pending_approval(payload.history) and _is_confirmation(payload.message):
        result = await _confirmed_refund_result(effective_customer_id)
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id, save_refund=True)

    if _wants_order_lookup(payload.message) or _is_customer_id_only(payload.message):
        result = await _order_lookup_response(effective_customer_id)
        return await _chat_response(session, effective_customer_id, payload.message, result, request_id)

    if _is_off_topic(payload.message):
        result = AgentResult(
            decision="none",
            reason=OFF_TOPIC_MESSAGE,
            escalated=False,
            model_used="topic-filter",
            policy_rule=None,
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
    if result.decision == "approved":
        result = await _approval_confirmation_prompt(result, effective_customer_id)
    return await _chat_response(session, effective_customer_id, payload.message, result, request_id, save_refund=True)


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
