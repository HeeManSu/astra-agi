"""
Calculate Shipping Tool - Shipping Agent.

Calculates shipping costs and estimated delivery times.
"""

from datetime import datetime, timedelta
import json

from framework.agents.tool import tool


# Mock shipping rates - in production, this would query shipping APIs
SHIPPING_RATES = {
    "US": {
        "standard": {"cost": 5.99, "days": 5},
        "express": {"cost": 12.99, "days": 2},
        "overnight": {"cost": 24.99, "days": 1},
    },
    "CA": {
        "standard": {"cost": 8.99, "days": 7},
        "express": {"cost": 19.99, "days": 3},
    },
    "UK": {
        "standard": {"cost": 9.99, "days": 10},
        "express": {"cost": 24.99, "days": 5},
    },
    "AU": {
        "standard": {"cost": 12.99, "days": 14},
        "express": {"cost": 29.99, "days": 7},
    },
    "DE": {
        "standard": {"cost": 7.99, "days": 8},
        "express": {"cost": 18.99, "days": 4},
    },
    "FR": {
        "standard": {"cost": 7.99, "days": 8},
        "express": {"cost": 18.99, "days": 4},
    },
}


@tool(
    name="calculate_shipping",
    description=(
        "Calculate shipping costs and estimated delivery times based on "
        "destination, weight, and shipping method."
    ),
)
async def calculate_shipping(
    destination_country: str,
    weight_kg: float,
    shipping_method: str = "standard",
) -> str:
    """
    Calculate shipping costs and delivery estimate.

    Args:
        destination_country: Destination country code (US, CA, UK, etc.)
        weight_kg: Package weight in kilograms
        shipping_method: Shipping method (standard, express, overnight)

    Returns:
        JSON string with shipping cost and estimated delivery date
    """
    country = destination_country.upper()

    if country not in SHIPPING_RATES:
        return json.dumps(
            {
                "status": "error",
                "error": f"Shipping to {country} is not available",
                "cost": None,
                "estimated_delivery": None,
            },
            indent=2,
        )

    country_rates = SHIPPING_RATES[country]

    if shipping_method not in country_rates:
        available_methods = ", ".join(country_rates.keys())
        return json.dumps(
            {
                "status": "error",
                "error": (
                    f"Shipping method '{shipping_method}' not available for {country}. "
                    f"Available: {available_methods}"
                ),
                "cost": None,
                "estimated_delivery": None,
            },
            indent=2,
        )

    rate_info = country_rates[shipping_method]
    base_cost = rate_info["cost"]

    # Add weight-based surcharge (for demo purposes)
    # In production, this would use actual shipping API calculations
    weight_surcharge = max(0, (weight_kg - 1.0) * 2.0)  # $2 per kg over 1kg
    total_cost = base_cost + weight_surcharge

    # Calculate estimated delivery date
    delivery_days = rate_info["days"]
    estimated_delivery = datetime.now() + timedelta(days=delivery_days)

    return json.dumps(
        {
            "status": "success",
            "destination_country": country,
            "shipping_method": shipping_method,
            "weight_kg": weight_kg,
            "base_cost": base_cost,
            "weight_surcharge": weight_surcharge,
            "total_cost": round(total_cost, 2),
            "currency": "USD",
            "estimated_delivery_days": delivery_days,
            "estimated_delivery_date": estimated_delivery.strftime("%Y-%m-%d"),
            "calculated_at": datetime.now().isoformat(),
        },
        indent=2,
    )
