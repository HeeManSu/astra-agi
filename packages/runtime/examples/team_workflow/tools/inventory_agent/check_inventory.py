"""
Check Inventory Tool - Inventory Agent.

Checks stock availability for products.
"""

from datetime import datetime
import json

from framework.agents.tool import tool


# Mock inventory database - in production, this would query a real database
INVENTORY = {
    "PROD-001": {"name": "Laptop", "stock": 50, "reserved": 5},
    "PROD-002": {"name": "Mouse", "stock": 200, "reserved": 20},
    "PROD-003": {"name": "Keyboard", "stock": 150, "reserved": 10},
    "PROD-004": {"name": "Monitor", "stock": 75, "reserved": 8},
    "PROD-005": {"name": "Headphones", "stock": 300, "reserved": 15},
}


@tool(
    name="check_inventory",
    description=(
        "Check stock availability for products. Returns available quantity "
        "and stock status for each product."
    ),
)
async def check_inventory(product_ids: list[str]) -> str:
    """
    Check inventory for multiple products.

    Args:
        product_ids: List of product IDs to check

    Returns:
        JSON string with inventory status for each product
    """
    results = []
    checked_at = datetime.now().isoformat()

    for product_id in product_ids:
        if product_id in INVENTORY:
            product = INVENTORY[product_id]
            available = product["stock"] - product["reserved"]
            results.append(
                {
                    "product_id": product_id,
                    "name": product["name"],
                    "total_stock": product["stock"],
                    "reserved": product["reserved"],
                    "available": available,
                    "in_stock": available > 0,
                    "status": "in_stock" if available > 0 else "out_of_stock",
                }
            )
        else:
            results.append(
                {
                    "product_id": product_id,
                    "name": "Unknown Product",
                    "status": "not_found",
                    "available": 0,
                    "in_stock": False,
                }
            )

    return json.dumps(
        {"products": results, "checked_at": checked_at},
        indent=2,
    )
