"""
Validate Order Tool - Order Validator Agent.

Validates order details, customer information, and order requirements.
"""

from datetime import datetime
import json

from framework.agents.tool import tool


# Mock order validation rules - in production, this would query a database
VALIDATION_RULES = {
    "min_order_value": 5.0,
    "max_order_value": 10000.0,
    "required_fields": ["customer_id", "items", "shipping_address"],
    "allowed_countries": ["US", "CA", "UK", "AU", "DE", "FR"],
}


@tool(
    name="validate_order",
    description=(
        "Validate order details including customer information, items, "
        "and shipping address. Returns validation status and any errors."
    ),
)
async def validate_order(
    order_id: str,
    customer_id: str,
    items: list[dict],
    shipping_address: dict,
    payment_method: str | None = None,
) -> str:
    """
    Validate an order.

    Args:
        order_id: Unique order identifier
        customer_id: Customer ID
        items: List of items with product_id, quantity, price
        shipping_address: Shipping address dictionary
        payment_method: Optional payment method

    Returns:
        JSON string with validation status and any errors
    """
    errors = []
    warnings = []

    # Validate order value
    total_value = sum(item.get("price", 0) * item.get("quantity", 0) for item in items)
    if total_value < VALIDATION_RULES["min_order_value"]:
        errors.append(
            f"Order value ${total_value:.2f} is below minimum "
            f"${VALIDATION_RULES['min_order_value']:.2f}"
        )
    if total_value > VALIDATION_RULES["max_order_value"]:
        warnings.append(
            f"Order value ${total_value:.2f} exceeds maximum "
            f"${VALIDATION_RULES['max_order_value']:.2f} - requires manual review"
        )

    # Validate required fields
    if not customer_id:
        errors.append("customer_id is required")
    if not items or len(items) == 0:
        errors.append("Order must contain at least one item")
    if not shipping_address:
        errors.append("shipping_address is required")

    # Validate shipping address
    if shipping_address:
        country = shipping_address.get("country", "").upper()
        if country not in VALIDATION_RULES["allowed_countries"]:
            errors.append(
                f"Shipping to country '{country}' is not supported. "
                f"Allowed countries: {', '.join(VALIDATION_RULES['allowed_countries'])}"
            )

    # Validate items
    for idx, item in enumerate(items):
        if "product_id" not in item:
            errors.append(f"Item {idx + 1}: product_id is required")
        if "quantity" not in item or item["quantity"] <= 0:
            errors.append(f"Item {idx + 1}: quantity must be greater than 0")
        if "price" not in item or item["price"] < 0:
            errors.append(f"Item {idx + 1}: price must be non-negative")

    # Determine validation status
    is_valid = len(errors) == 0
    status = "valid" if is_valid else "invalid"

    result = {
        "order_id": order_id,
        "status": status,
        "is_valid": is_valid,
        "total_value": total_value,
        "validated_at": datetime.now().isoformat(),
        "errors": errors,
        "warnings": warnings,
    }

    return json.dumps(result, indent=2)
