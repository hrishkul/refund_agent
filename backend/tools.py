from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from sqlalchemy import text

from database import AsyncSessionLocal


POLICY_PATH = Path(__file__).with_name("policy.txt")


async def get_customer_order_data(customer_id: str) -> dict:
    query = text(
        """
        SELECT c.id AS customer_id, c.full_name, c.is_premium, o.id AS order_id,
               o.status, o.total_amount, o.created_at, o.shipped_at, o.delivered_at,
               oi.id AS order_item_id, oi.is_defective, oi.downloaded_at,
               p.name, p.is_final_sale, p.is_digital, p.price
        FROM orders o JOIN customers c ON o.customer_id = c.id
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p ON oi.product_id = p.id
        WHERE c.id::text = :customer_id OR lower(split_part(c.email, '@', 1)) = lower(:customer_id)
        ORDER BY o.created_at DESC LIMIT 1
        """
    )
    async with AsyncSessionLocal() as session:
        row = (await session.execute(query, {"customer_id": customer_id})).mappings().first()
    if not row:
        return {"found": False, "customer_id": customer_id}
    created_at = row["created_at"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return {
        "found": True,
        "customer_id": str(row["customer_id"]),
        "order_id": str(row["order_id"]),
        "order_item_id": str(row["order_item_id"]),
        "customer_name": row["full_name"],
        "is_premium": row["is_premium"],
        "order_status": row["status"],
        "total_amount": float(row["total_amount"]),
        "days_since_order": (datetime.now(timezone.utc) - created_at).days,
        "product_name": row["name"],
        "is_final_sale": row["is_final_sale"],
        "is_digital": row["is_digital"],
        "is_defective": row["is_defective"],
        "downloaded_at": row["downloaded_at"].isoformat() if row["downloaded_at"] else None,
        "shipped_at": row["shipped_at"].isoformat() if row["shipped_at"] else None,
        "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
    }


def check_refund_policy_data(order_details: dict) -> dict:
    POLICY_PATH.read_text()
    if not order_details.get("found"):
        return {
            "eligible": False,
            "recommendation": "denied",
            "rule_violated": "customer_not_found",
            "rule_number": None,
        }

    if "days_since_order" in order_details:
        age_days = int(order_details["days_since_order"])
    else:
        created_at = datetime.fromisoformat(str(order_details["created_at"]).replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created_at).days
    total_amount = float(order_details["total_amount"])
    order_status = order_details.get("order_status") or order_details.get("status")

    if order_details.get("is_final_sale"):
        return {"eligible": False, "recommendation": "denied", "rule_violated": "final_sale", "rule_number": 1}
    if order_details.get("is_defective") and age_days <= 60:
        return {"eligible": True, "recommendation": "approved", "rule_violated": None, "rule_number": None}
    if total_amount > 500:
        return {"eligible": False, "recommendation": "escalated", "rule_violated": "high_value_refund", "rule_number": 3}
    if order_details.get("is_digital") and order_details.get("downloaded_at"):
        return {"eligible": False, "recommendation": "denied", "rule_violated": "downloaded_digital_product", "rule_number": 5}
    return_window = 45 if order_details.get("is_premium") else 30
    if age_days > return_window:
        return {"eligible": False, "recommendation": "denied", "rule_violated": "outside_return_window", "rule_number": 2}
    if order_status == "shipped" and not order_details.get("delivered_at"):
        return {"eligible": False, "recommendation": "denied", "rule_violated": "shipped_not_delivered", "rule_number": 6}
    if order_status != "delivered":
        return {"eligible": False, "recommendation": "denied", "rule_violated": "order_not_delivered", "rule_number": None}
    return {"eligible": True, "recommendation": "approved", "rule_violated": None, "rule_number": None}


@tool
async def get_customer_order(customer_id: Annotated[str, "Customer UUID"]) -> dict:
    """Fetch the latest customer order with product and item details."""
    return await get_customer_order_data(customer_id)


@tool
def check_refund_policy(order_details: Annotated[dict, "Order details from get_customer_order"]) -> dict:
    """Evaluate order details against refund policy rules."""
    return check_refund_policy_data(order_details)
