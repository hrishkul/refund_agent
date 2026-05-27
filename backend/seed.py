import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Customer, Order, OrderItem, OrderStatus, Product


NS = uuid.UUID("2f25c8be-3eb8-4e49-9a31-3fa471daed51")


def uid(name: str) -> uuid.UUID:
    return uuid.uuid5(NS, name)


async def seed_data(session: AsyncSession) -> None:
    existing = await session.scalar(select(Customer.id).limit(1))
    if existing:
        return

    now = datetime.now(timezone.utc)
    product_specs = {
        "standard": ("Everyday Hoodie", "clothing", "89.00", False, False),
        "final": ("Final Sale Sneakers", "clothing", "120.00", True, False),
        "premium": ("Noise Cancelling Headphones", "electronics", "240.00", False, False),
        "expensive": ("OLED Monitor", "electronics", "750.00", False, False),
        "digital": ("Design Template Pack", "digital", "49.00", False, True),
        "defective": ("Smart Kettle", "electronics", "99.00", False, False),
    }
    products = {}
    for key, (name, category, price, final_sale, digital) in product_specs.items():
        product = Product(
            id=uid(f"product-{key}"),
            name=name,
            category=category,
            price=Decimal(price),
            is_final_sale=final_sale,
            is_digital=digital,
            description=f"Seed product for {key} refund scenarios.",
        )
        products[key] = product
        session.add(product)

    scenarios = [
        ("C001", "Ava Eligible", False, "standard", OrderStatus.delivered, 10, 8, None, False),
        ("C002", "Ben Finalsale", False, "final", OrderStatus.delivered, 8, 5, None, False),
        ("C003", "Cara Late", False, "standard", OrderStatus.delivered, 35, 32, None, False),
        ("C004", "Dev Escalate", False, "expensive", OrderStatus.delivered, 12, 10, None, False),
        ("C005", "Eli Digital", False, "digital", OrderStatus.delivered, 3, 2, now - timedelta(days=2), False),
        ("C006", "Faye Defective", False, "defective", OrderStatus.delivered, 50, 48, None, True),
        ("C007", "Gia Shipped", False, "standard", OrderStatus.shipped, 2, None, None, False),
        ("C008", "Hari Premium", True, "premium", OrderStatus.delivered, 40, 37, None, False),
        ("C009", "Ira Pending", False, "standard", OrderStatus.pending, 1, None, None, False),
        ("C010", "Jules Processing", False, "premium", OrderStatus.processing, 4, None, None, False),
        ("C011", "Kai Delivered", False, "premium", OrderStatus.delivered, 15, 12, None, False),
        ("C012", "Lena Cancelled", False, "standard", OrderStatus.cancelled, 5, None, None, False),
        ("C013", "Mina Delivered", False, "standard", OrderStatus.delivered, 25, 21, None, False),
        ("C014", "Noah Premium", True, "standard", OrderStatus.delivered, 44, 42, None, False),
        ("C015", "Omar Late", False, "premium", OrderStatus.delivered, 70, 66, None, False),
    ]

    for code, name, premium, product_key, status, order_age, delivered_age, downloaded_at, defective in scenarios:
        customer = Customer(
            id=uid(f"customer-{code}"),
            email=f"{code.lower()}@worknoon.local",
            full_name=name,
            phone=f"+1-555-{code[-3:]}",
            is_premium=premium,
        )
        product = products[product_key]
        created_at = now - timedelta(days=order_age)
        delivered_at = now - timedelta(days=delivered_age) if delivered_age else None
        shipped_at = created_at + timedelta(days=2) if status in {OrderStatus.shipped, OrderStatus.delivered} else None
        order = Order(
            id=uid(f"order-{code}"),
            customer_id=customer.id,
            status=status,
            total_amount=product.price,
            created_at=created_at,
            shipped_at=shipped_at,
            delivered_at=delivered_at,
            shipping_address=f"{code} Market Street, San Francisco, CA",
        )
        item = OrderItem(
            id=uid(f"item-{code}"),
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price=product.price,
            is_defective=defective,
            downloaded_at=downloaded_at,
        )
        session.add_all([customer, order, item])

    await session.commit()
