"""
Generate Shipping Label Tool - Shipping Agent.

Generates shipping labels for orders. This is an async operation.
"""

import asyncio
from datetime import datetime
import json
import uuid

from framework.agents.tool import tool


# Mock label storage
SHIPPING_LABELS = []


@tool(
    name="generate_label",
    description=(
        "Generate shipping label for an order. Simulates async label "
        "generation. Returns label ID and tracking number."
    ),
)
async def generate_label(
    order_id: str,
    shipping_address: dict,
    weight_kg: float,
    carrier: str = "USPS",
) -> str:
    """
    Generate shipping label (async operation).

    Args:
        order_id: Order ID
        shipping_address: Shipping address dictionary
        weight_kg: Package weight in kilograms
        carrier: Shipping carrier (USPS, FedEx, UPS, DHL)

    Returns:
        JSON string with label ID and tracking number
    """
    # Simulate async label generation delay
    # Reason: Label generation involves API calls to shipping carriers
    await asyncio.sleep(0.6)

    label_id = f"LABEL-{str(uuid.uuid4())[:8].upper()}"
    tracking_number = f"{carrier}-{str(uuid.uuid4()).upper()[:12]}"

    label = {
        "label_id": label_id,
        "order_id": order_id,
        "tracking_number": tracking_number,
        "carrier": carrier,
        "shipping_address": shipping_address,
        "weight_kg": weight_kg,
        "status": "generated",
        "generated_at": datetime.now().isoformat(),
        "label_url": f"https://labels.example.com/{label_id}",  # Mock URL
    }

    SHIPPING_LABELS.append(label)

    return json.dumps(label, indent=2)
