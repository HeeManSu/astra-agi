"""
Reserve Items Tool - Inventory Agent.

Reserves items in inventory for an order.
"""

from datetime import datetime
import json
import uuid

from framework.agents.tool import tool


# Mock inventory database (shared with check_inventory)
INVENTORY = {
    "PROD-001": {"name": "Laptop", "stock": 50, "reserved": 5},
    "PROD-002": {"name": "Mouse", "stock": 200, "reserved": 20},
    "PROD-003": {"name": "Keyboard", "stock": 150, "reserved": 10},
    "PROD-004": {"name": "Monitor", "stock": 75, "reserved": 8},
    "PROD-005": {"name": "Headphones", "stock": 300, "reserved": 15},
}

# Mock reservation storage
RESERVATIONS = []


@tool(
    name="reserve_items",
    description=(
        "Reserve items in inventory for an order. Returns reservation ID "
        "and confirmation of reserved quantities."
    ),
)
async def reserve_items(order_id: str, items: list[dict]) -> str:
    """
    Reserve items in inventory.

    Args:
        order_id: Order ID for this reservation
        items: List of items with product_id and quantity

    Returns:
        JSON string with reservation status
    """
    reservation_id = str(uuid.uuid4())[:8].upper()
    reserved_items = []
    errors = []

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 0)

        if product_id not in INVENTORY:
            errors.append(f"Product {product_id} not found")
            continue

        product = INVENTORY[product_id]
        available = product["stock"] - product["reserved"]

        if available < quantity:
            errors.append(
                f"Insufficient stock for {product_id}: "
                f"requested {quantity}, available {available}"
            )
            continue

        # Reserve the items
        product["reserved"] += quantity
        reserved_items.append(
            {
                "product_id": product_id,
                "name": product["name"],
                "quantity": quantity,
                "reserved": True,
            }
        )

    if errors:
        # Rollback reservations if any failed
        for reserved_item in reserved_items:
            product_id = reserved_item["product_id"]
            quantity = reserved_item["quantity"]
            INVENTORY[product_id]["reserved"] -= quantity

        return json.dumps(
            {
                "reservation_id": reservation_id,
                "status": "failed",
                "errors": errors,
                "reserved_items": [],
            },
            indent=2,
        )

    # Store reservation
    reservation = {
        "reservation_id": reservation_id,
        "order_id": order_id,
        "items": reserved_items,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    RESERVATIONS.append(reservation)

    return json.dumps(
        {
            "reservation_id": reservation_id,
            "status": "success",
            "reserved_items": reserved_items,
            "reserved_at": datetime.now().isoformat(),
        },
        indent=2,
    )
