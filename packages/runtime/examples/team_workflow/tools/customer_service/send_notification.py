"""
Send Notification Tool - Customer Service Agent.

Sends notifications to customers via email or SMS. This is an async operation.
"""

import asyncio
from datetime import datetime
import json
import uuid

from framework.agents.tool import tool


# Mock notification storage
NOTIFICATIONS = []


@tool(
    name="send_notification",
    description=(
        "Send notification to customer via email or SMS. Simulates async "
        "notification service. Returns notification ID and status."
    ),
)
async def send_notification(
    customer_id: str,
    notification_type: str,
    message: str,
    channel: str = "email",
    order_id: str | None = None,
) -> str:
    """
    Send notification to customer (async operation).

    Args:
        customer_id: Customer ID
        notification_type: Type of notification (order_confirmed, shipped, delivered, etc.)
        message: Notification message
        channel: Notification channel (email, sms, push)
        order_id: Optional order ID for order-related notifications

    Returns:
        JSON string with notification status
    """
    # Simulate async notification sending delay
    # Reason: Email/SMS services take time to process
    await asyncio.sleep(0.3)

    notification_id = f"NOTIF-{str(uuid.uuid4())[:8].upper()}"

    notification = {
        "notification_id": notification_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "type": notification_type,
        "channel": channel,
        "message": message,
        "status": "sent",
        "sent_at": datetime.now().isoformat(),
    }

    NOTIFICATIONS.append(notification)

    return json.dumps(notification, indent=2)
