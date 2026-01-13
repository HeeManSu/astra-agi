"""
Process Payment Tool - Payment Agent.

Processes payment for an order. This is an async operation simulating
real payment gateway interaction.
"""

import asyncio
from datetime import datetime
import json
import uuid

from framework.agents.tool import tool


# Mock payment storage
PAYMENTS = []


@tool(
    name="process_payment",
    description=(
        "Process payment for an order. Simulates async payment gateway "
        "interaction. Returns payment ID and transaction status."
    ),
)
async def process_payment(
    order_id: str,
    amount: float,
    payment_method: str,
    customer_id: str,
    currency: str = "USD",
) -> str:
    """
    Process payment for an order (async operation).

    This simulates a real payment gateway that takes time to process.
    In production, this would call an actual payment API.

    Args:
        order_id: Order ID
        amount: Payment amount
        payment_method: Payment method (credit_card, debit_card, paypal, etc.)
        customer_id: Customer ID
        currency: Currency code (default: USD)

    Returns:
        JSON string with payment status and transaction ID
    """
    # Simulate async payment processing delay
    # Reason: Real payment gateways take time to process
    await asyncio.sleep(0.5)  # Simulate network delay

    transaction_id = str(uuid.uuid4())[:8].upper()
    payment_id = f"PAY-{transaction_id}"

    # Simulate payment validation
    # In production, this would validate with payment gateway
    if amount <= 0:
        return json.dumps(
            {
                "payment_id": payment_id,
                "order_id": order_id,
                "status": "failed",
                "error": "Payment amount must be greater than 0",
                "transaction_id": None,
            },
            indent=2,
        )

    if amount > 10000:
        # Simulate high-value payment requiring additional verification
        await asyncio.sleep(0.3)  # Additional verification delay

    # Simulate payment success (90% success rate for demo)
    # In production, this would be determined by actual payment gateway
    import random

    is_successful = random.random() > 0.1  # 90% success rate

    if is_successful:
        status = "completed"
        error = None
    else:
        status = "failed"
        error = "Payment gateway declined transaction"

    payment = {
        "payment_id": payment_id,
        "order_id": order_id,
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "customer_id": customer_id,
        "status": status,
        "error": error,
        "processed_at": datetime.now().isoformat(),
    }

    PAYMENTS.append(payment)

    return json.dumps(payment, indent=2)
