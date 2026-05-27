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


@tool
async def get_customer_order(customer_id: Annotated[str, "Customer UUID or email prefix"]) -> dict:
    """Fetch the latest customer order with product and item details."""
    return await get_customer_order_data(customer_id)


@tool
def get_refund_policy() -> str:
    """Return the full ShopEase refund policy text so you can reason over it."""
    return POLICY_PATH.read_text()
