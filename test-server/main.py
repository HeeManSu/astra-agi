"""
Customer Support Agent - Astra Server with Playground

Run with: python main.py
Playground: http://localhost:8000/playground
API Docs: http://localhost:8000/docs
"""

from datetime import datetime, timedelta
import os
from random import randint

from astra import Agent, AgentStorage, Gemini, MongoDBStorage, tool
from astra.server import AstraServer, ServerConfig


# ========== TOOLS ==========


@tool
def get_order_status(order_id: str) -> str:
    """
    Get the status of a customer order by order ID.

    Args:
        order_id: The order ID (e.g., ORD-12345)
    """
    orders = {
        "ORD-12345": {"status": "Shipped", "carrier": "FedEx", "eta": "Jan 8, 2025"},
        "ORD-67890": {"status": "Processing", "carrier": None, "eta": "Jan 10, 2025"},
        "ORD-11111": {"status": "Delivered", "carrier": "UPS", "eta": "Delivered Jan 3"},
        "ORD-22222": {"status": "Cancelled", "carrier": None, "eta": None},
    }

    order = orders.get(order_id.upper())
    if order:
        status = order["status"]
        if status == "Shipped":
            carrier = order["carrier"]
            eta = order["eta"]
            return f"Order {order_id}: {status} via {carrier}. Expected delivery: {eta}"
        elif status == "Delivered":
            eta = order["eta"]
            return f"Order {order_id}: {status}! {eta}"
        else:
            eta = order["eta"]
            eta_msg = f"ETA: {eta}" if eta else ""
            return f"Order {order_id}: {status}. {eta_msg}"

    return f"Order {order_id} not found. Please check your order ID."


@tool
def get_product_info(product_name: str) -> str:
    """
    Get detailed information about a product.

    Args:
        product_name: Name or keyword of the product to search
    """
    products = {
        "laptop": {
            "name": "ProBook X1 Laptop",
            "price": 1299.99,
            "stock": "In Stock",
            "specs": "16GB RAM, 512GB SSD, Intel i7, 15.6 inch display",
            "rating": 4.8,
        },
        "headphones": {
            "name": "SoundMax Pro Wireless",
            "price": 249.99,
            "stock": "In Stock",
            "specs": "Active Noise Cancellation, 40hr battery, Bluetooth 5.3",
            "rating": 4.6,
        },
        "keyboard": {
            "name": "MechBoard Elite",
            "price": 179.99,
            "stock": "Low Stock (5 left)",
            "specs": "Mechanical Cherry MX switches, RGB, wireless",
            "rating": 4.9,
        },
        "monitor": {
            "name": "UltraView 4K",
            "price": 599.99,
            "stock": "Out of Stock",
            "specs": "32 inch 4K IPS, 144Hz, HDR10, USB-C",
            "rating": 4.7,
        },
    }

    key = product_name.lower()
    for k, v in products.items():
        if k in key or key in k:
            name = v["name"]
            price = v["price"]
            stock = v["stock"]
            specs = v["specs"]
            rating = v["rating"]
            return f"**{name}**\n- Price: ${price:.2f}\n- Availability: {stock}\n- Specs: {specs}\n- Rating: {rating}/5"

    return (
        f"No products found matching '{product_name}'. Try: laptop, headphones, keyboard, monitor"
    )


@tool
def initiate_return(order_id: str, reason: str) -> str:
    """
    Initiate a return request for an order.

    Args:
        order_id: The order ID to return
        reason: Reason for the return
    """
    ticket_id = f"RET-{randint(10000, 99999)}"

    return f"""Return Request Created

- Return Ticket: {ticket_id}
- Order: {order_id}
- Reason: {reason}
- Status: Pending Approval

Next steps:
1. You will receive a confirmation email within 24 hours
2. Print the return label (will be emailed)
3. Drop off at any FedEx location
4. Refund will be processed within 5-7 business days"""


@tool
def check_warranty(product_name: str, purchase_date: str) -> str:
    """
    Check if a product is still under warranty.

    Args:
        product_name: Name of the product
        purchase_date: Date of purchase (YYYY-MM-DD format)
    """
    try:
        purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
        warranty_end = purchase + timedelta(days=365)
        today = datetime.now()

        if today < warranty_end:
            days_left = (warranty_end - today).days
            end_date = warranty_end.strftime("%B %d, %Y")
            return (
                f"{product_name} is under warranty! {days_left} days remaining (expires {end_date})"
            )
        else:
            days_expired = (today - warranty_end).days
            end_date = warranty_end.strftime("%B %d, %Y")
            return f"Warranty for {product_name} expired {days_expired} days ago on {end_date}"
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-06-15)"


@tool
def get_store_hours(location: str) -> str:
    """
    Get store hours for a specific location.

    Args:
        location: City or store name
    """
    stores = {
        "new york": "NYC Flagship: Mon-Sat 10am-9pm, Sun 11am-7pm | 350 5th Avenue",
        "los angeles": "LA Store: Mon-Sat 10am-8pm, Sun 12pm-6pm | 8500 Beverly Blvd",
        "chicago": "Chicago Loop: Mon-Sat 9am-8pm, Sun 11am-6pm | 111 N State St",
        "online": "24/7 at www.example-store.com | Free shipping on orders $50+",
    }

    for key, value in stores.items():
        if key in location.lower():
            return value

    return f"Store not found in '{location}'. Available: New York, Los Angeles, Chicago, Online"


@tool
def get_faq_answer(topic: str) -> str:
    """
    Get answers to frequently asked questions.

    Args:
        topic: Topic or keyword for FAQ (shipping, returns, payment, etc.)
    """
    faqs = {
        "shipping": "Free shipping on orders $50+. Standard: 5-7 days. Express: 2-3 days ($12.99).",
        "returns": "30-day returns on unused items. Electronics: 15 days. Free return shipping for defects.",
        "payment": "Credit/debit, PayPal, Apple Pay, Google Pay. Klarna available for orders $35+.",
        "warranty": "1-year warranty on electronics. 2-year on appliances. Extended plans available.",
    }

    for key, value in faqs.items():
        if key in topic.lower():
            return value

    return f"FAQ topic '{topic}' not found. Try: shipping, returns, payment, warranty"


# ========== AGENT ==========


def create_support_agent() -> Agent:
    """Create the customer support agent."""
    return Agent(
        name="SupportBot",
        model=Gemini("gemini-2.5-flash"),
        instructions="""You are SupportBot, a friendly customer support assistant.

Help customers with:
- Order tracking (test IDs: ORD-12345, ORD-67890, ORD-11111, ORD-22222)
- Product info (laptop, headphones, keyboard, monitor)
- Returns and refunds
- Warranty checks
- Store hours
- FAQs (shipping, returns, payment, warranty)

Be polite, helpful, and use tools to provide accurate information.""",
        tools=[
            get_order_status,
            get_product_info,
            initiate_return,
            check_warranty,
            get_store_hours,
            get_faq_answer,
        ],
    )


# ========== SERVER ==========


def main() -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        print("Please set GOOGLE_API_KEY environment variable")
        print("   export GOOGLE_API_KEY='your-api-key'")
        return

    # Get MongoDB URL from env or use localhost
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

    # Create MongoDB storage backend
    mongo_storage = MongoDBStorage(
        url=mongo_url,
        db_name="astra_db",
    )

    # Wrap in AgentStorage facade (provides thread methods like list_threads, etc.)
    storage = AgentStorage(storage=mongo_storage)

    # Create agent
    support_agent = create_support_agent()

    # Create server with playground enabled and storage
    server = AstraServer(
        agents={"support": support_agent},
        storage=storage,
        config=ServerConfig(
            name="Customer Support API",
            description="AI-powered customer support with playground",
            version="1.0.0",
            docs_enabled=True,
            playground_enabled=True,
            cors_origins=["*"],
            jwt_secret=os.getenv("ASTRA_JWT_SECRET", "dev-secret-change-in-production"),
        ),
    )

    app = server.create_app()

    print("=" * 60)
    print("Customer Support Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  Playground: http://localhost:8000/playground")
    print("  API Docs:   http://localhost:8000/docs")
    print("  Invoke:     POST /agents/support/invoke")
    print("-" * 60)
    print("\nStarting server at http://localhost:8000\n")

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
