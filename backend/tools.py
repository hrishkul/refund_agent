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
               oi.id AS order_item_id, oi.is_defective, oi.downloaded_at, oi.returned_at,
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
        "is_returned": row["returned_at"] is not None,
        "downloaded_at": row["downloaded_at"].isoformat() if row["downloaded_at"] else None,
        "returned_at": row["returned_at"].isoformat() if row["returned_at"] else None,
        "shipped_at": row["shipped_at"].isoformat() if row["shipped_at"] else None,
        "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
    }


async def mark_latest_order_returned(customer_id: str) -> dict:
    order = await get_customer_order_data(customer_id)
    if not order.get("found"):
        return order
    if order.get("is_returned"):
        return order

    update = text(
        """
        UPDATE order_items
        SET returned_at = now()
        WHERE id = :order_item_id
        """
    )
    async with AsyncSessionLocal() as session:
        await session.execute(update, {"order_item_id": order["order_item_id"]})
        await session.commit()

    return await get_customer_order_data(customer_id)


def check_refund_policy_data(order: dict) -> dict:
    if not order.get("found"):
        return {
            "eligible": False,
            "recommendation": "denied",
            "rule_violated": "order_not_found",
            "rule_number": None,
        }

    days_since_order = int(order.get("days_since_order") or 0)
    total_amount = float(order.get("total_amount") or 0)
    order_status = order.get("order_status")

    if order.get("is_final_sale"):
        return {
            "eligible": False,
            "recommendation": "denied",
            "rule_violated": "final_sale",
            "rule_number": 1,
        }

    if order_status == "shipped":
        return {
            "eligible": False,
            "recommendation": "denied",
            "rule_violated": "shipped_not_delivered",
            "rule_number": 6,
        }

    if order_status != "delivered":
        return {
            "eligible": False,
            "recommendation": "denied",
            "rule_violated": "not_delivered",
            "rule_number": 6,
        }

    if order.get("is_defective") and days_since_order <= 60:
        return {
            "eligible": True,
            "recommendation": "approved",
            "rule_violated": None,
            "rule_number": 4,
        }

    if total_amount > 500:
        return {
            "eligible": False,
            "recommendation": "escalated",
            "rule_violated": "high_value_refund",
            "rule_number": 3,
        }

    if order.get("is_digital") and order.get("downloaded_at"):
        return {
            "eligible": False,
            "recommendation": "denied",
            "rule_violated": "downloaded_digital_product",
            "rule_number": 5,
        }

    window_days = 45 if order.get("is_premium") else 30
    if days_since_order <= window_days:
        return {
            "eligible": True,
            "recommendation": "approved",
            "rule_violated": None,
            "rule_number": 2,
        }

    return {
        "eligible": False,
        "recommendation": "denied",
        "rule_violated": "outside_return_window",
        "rule_number": 2,
    }


@tool
async def get_customer_order(customer_id: Annotated[str, "Customer UUID or email prefix"]) -> dict:
    """Fetch the latest customer order with product and item details."""
    return await get_customer_order_data(customer_id)


@tool
def get_refund_policy() -> str:
    """Return the full ShopEase refund policy text so you can reason over it."""
    return POLICY_PATH.read_text()
