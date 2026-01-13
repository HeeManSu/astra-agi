"""
Refund Payment Tool - Payment Agent.

Processes refunds for orders. This is an async operation.
"""

import asyncio
from datetime import datetime
import json
import uuid

from framework.agents.tool import tool


# Mock payment storage (shared with process_payment)
PAYMENTS = []


@tool(
    name="refund_payment",
    description=(
        "Process a refund for a payment. Simulates async refund processing. "
        "Returns refund ID and status."
    ),
)
async def refund_payment(
    payment_id: str,
    amount: float | None = None,
    reason: str | None = None,
) -> str:
    """
    Process a refund (async operation).

    Args:
        payment_id: Original payment ID to refund
        amount: Refund amount (if None, refunds full amount)
        reason: Optional refund reason

    Returns:
        JSON string with refund status
    """
    # Simulate async refund processing delay
    await asyncio.sleep(0.4)

    # Find original payment
    original_payment = None
    for payment in PAYMENTS:
        if payment["payment_id"] == payment_id:
            original_payment = payment
            break

    if not original_payment:
        return json.dumps(
            {
                "refund_id": None,
                "status": "failed",
                "error": f"Payment {payment_id} not found",
            },
            indent=2,
        )

    if original_payment["status"] != "completed":
        return json.dumps(
            {
                "refund_id": None,
                "status": "failed",
                "error": f"Payment {payment_id} is not completed, cannot refund",
            },
            indent=2,
        )

    # Determine refund amount
    refund_amount = amount if amount is not None else original_payment["amount"]

    if refund_amount > original_payment["amount"]:
        return json.dumps(
            {
                "refund_id": None,
                "status": "failed",
                "error": (
                    f"Refund amount ${refund_amount:.2f} exceeds "
                    f"original payment ${original_payment['amount']:.2f}"
                ),
            },
            indent=2,
        )

    refund_id = f"REF-{str(uuid.uuid4())[:8].upper()}"

    refund = {
        "refund_id": refund_id,
        "payment_id": payment_id,
        "order_id": original_payment["order_id"],
        "amount": refund_amount,
        "currency": original_payment["currency"],
        "reason": reason or "Customer request",
        "status": "completed",
        "processed_at": datetime.now().isoformat(),
    }

    PAYMENTS.append(refund)

    return json.dumps(refund, indent=2)
