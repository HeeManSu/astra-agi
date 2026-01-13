"""
Update Order Status Tool - Customer Service Agent.

Updates order status in the system.
"""

from datetime import datetime
import json

from framework.agents.tool import tool


# Mock order storage
ORDERS = {}


@tool(
    name="update_order_status",
    description=("Update order status in the system. Returns updated order information."),
)
async def update_order_status(
    order_id: str,
    status: str,
    notes: str | None = None,
) -> str:
    """
    Update order status.

    Args:
        order_id: Order ID
        status: New status (pending, processing, shipped, delivered, cancelled)
        notes: Optional status update notes

    Returns:
        JSON string with updated order status
    """
    # Initialize order if it doesn't exist
    if order_id not in ORDERS:
        ORDERS[order_id] = {
            "order_id": order_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "status_history": [],
        }

    order = ORDERS[order_id]

    # Add to status history
    order["status_history"].append(
        {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "notes": notes,
        }
    )

    # Update current status
    order["status"] = status
    order["updated_at"] = datetime.now().isoformat()
    if notes:
        order["notes"] = notes

    return json.dumps(order, indent=2)
