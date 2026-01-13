"""
Check Fraud Risk Tool - Fraud Detection Agent.

Analyzes orders for potential fraud indicators. This is an async operation.
"""

import asyncio
from datetime import datetime
import json
import uuid

from framework.agents.tool import tool


@tool(
    name="check_fraud_risk",
    description=(
        "Analyze order for fraud risk indicators. Simulates async fraud "
        "detection analysis. Returns risk score and flagged issues."
    ),
)
async def check_fraud_risk(
    order_id: str,
    customer_id: str,
    amount: float,
    payment_method: str,
    shipping_address: dict,
    billing_address: dict | None = None,
) -> str:
    """
    Check fraud risk for an order (async operation).

    Args:
        order_id: Order ID
        customer_id: Customer ID
        amount: Order amount
        payment_method: Payment method used
        shipping_address: Shipping address
        billing_address: Optional billing address

    Returns:
        JSON string with fraud risk assessment
    """
    # Simulate async fraud detection analysis delay
    # Reason: Fraud detection involves multiple checks and ML models
    await asyncio.sleep(0.7)

    analysis_id = f"FRAUD-{str(uuid.uuid4())[:8].upper()}"

    # Mock fraud risk analysis
    # In production, this would use ML models and fraud detection APIs
    risk_score = 0.0
    flags = []
    risk_level = "low"

    # Check 1: High-value orders
    if amount > 5000:
        risk_score += 20
        flags.append("High-value order (>$5000)")

    # Check 2: Address mismatch
    if billing_address:
        shipping_country = shipping_address.get("country", "").upper()
        billing_country = billing_address.get("country", "").upper()
        if shipping_country != billing_country:
            risk_score += 30
            flags.append("Shipping and billing countries differ")

    # Check 3: Payment method
    if payment_method.lower() in ["prepaid_card", "gift_card"]:
        risk_score += 25
        flags.append("High-risk payment method")

    # Check 4: New customer with high value
    # (In production, would check customer history)
    if amount > 1000:
        risk_score += 15
        flags.append("High-value order from potentially new customer")

    # Determine risk level
    if risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    result = {
        "analysis_id": analysis_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "flags": flags,
        "recommendation": ("manual_review" if risk_level in ["medium", "high"] else "approve"),
        "analyzed_at": datetime.now().isoformat(),
    }

    return json.dumps(result, indent=2)
