"""
Complex E-Commerce Agent Example - Comprehensive edge case testing.

Tests:
- Multiple tools (async and sync)
- Complex nested parameters (dicts, lists, Optional)
- Error handling scenarios
- Multiple sequential tool calls
- Edge cases (empty inputs, None values, invalid data)
- Type conversions and validations
- Tool interactions and dependencies
- Streaming responses
- External API calls
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import Agent, tool

# Try to import aiohttp for API calls
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("Warning: aiohttp not installed. Install with: pip install aiohttp")

# E-Commerce Tools with Edge Cases

@tool
async def search_products(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10
) -> str:
    """
    Search for products with filters.
    
    Args:
        query: Search query string
        category: Optional category filter
        min_price: Optional minimum price
        max_price: Optional maximum price
        limit: Maximum results (default: 10)
    """
    # Mock product database
    products_db = {
        "laptop": [
            {"id": "LAP001", "name": "MacBook Pro", "price": 1999.99, "category": "electronics", "stock": 5},
            {"id": "LAP002", "name": "Dell XPS", "price": 1299.99, "category": "electronics", "stock": 12},
            {"id": "LAP003", "name": "HP Spectre", "price": 899.99, "category": "electronics", "stock": 0},
        ],
        "phone": [
            {"id": "PHN001", "name": "iPhone 15", "price": 999.99, "category": "electronics", "stock": 20},
            {"id": "PHN002", "name": "Samsung Galaxy", "price": 799.99, "category": "electronics", "stock": 15},
        ],
        "book": [
            {"id": "BOK001", "name": "Python Guide", "price": 29.99, "category": "books", "stock": 50},
            {"id": "BOK002", "name": "AI Handbook", "price": 49.99, "category": "books", "stock": 30},
        ]
    }
    
    # Edge case: Empty query
    if not query or not query.strip():
        return "Error: Search query cannot be empty"
    
    query_lower = query.lower().strip()
    results = []
    
    # Search across all products
    for category_products in products_db.values():
        for product in category_products:
            if query_lower in product["name"].lower():
                # Apply filters
                if category and product["category"] != category.lower():
                    continue
                if min_price is not None and product["price"] < min_price:
                    continue
                if max_price is not None and product["price"] > max_price:
                    continue
                results.append(product)
    
    # Edge case: No results
    if not results:
        return f"No products found matching '{query}'"
    
    # Apply limit
    results = results[:limit]
    
    # Format results
    formatted = [f"{p['name']} (${p['price']:.2f}) - Stock: {p['stock']}" for p in results]
    return f"Found {len(results)} products:\n" + "\n".join(f"- {item}" for item in formatted)


@tool
async def check_inventory(product_id: str, quantity: int = 1) -> str:
    """
    Check product inventory availability.
    
    Args:
        product_id: Product ID to check
        quantity: Required quantity (default: 1)
    """
    # Mock inventory
    inventory = {
        "LAP001": 5,
        "LAP002": 12,
        "LAP003": 0,
        "PHN001": 20,
        "PHN002": 15,
        "BOK001": 50,
        "BOK002": 30,
    }
    
    # Edge case: Invalid product ID
    if not product_id or product_id not in inventory:
        return f"Error: Product '{product_id}' not found"
    
    # Edge case: Invalid quantity
    if quantity <= 0:
        return f"Error: Quantity must be greater than 0, got {quantity}"
    
    available = inventory[product_id]
    
    # Edge case: Out of stock
    if available == 0:
        return f"Product {product_id} is out of stock"
    
    # Edge case: Insufficient stock
    if quantity > available:
        return f"Insufficient stock: {available} available, {quantity} requested"
    
    return f"Product {product_id}: {available} available, {quantity} requested - OK"


@tool
async def create_order(
    customer_id: str,
    items: List[Dict[str, Any]],
    shipping_address: Dict[str, str],
    payment_method: str = "credit_card"
) -> str:
    """
    Create a new order with multiple items.
    
    Args:
        customer_id: Customer identifier
        items: List of items with 'product_id' and 'quantity'
        shipping_address: Dict with 'street', 'city', 'zip', 'country'
        payment_method: Payment method (default: credit_card)
    """
    # Edge case: Empty customer ID
    if not customer_id or not customer_id.strip():
        return "Error: Customer ID is required"
    
    # Edge case: Empty items list
    if not items or len(items) == 0:
        return "Error: Order must contain at least one item"
    
    # Edge case: Invalid items structure
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return f"Error: Item {i} must be a dictionary"
        if "product_id" not in item:
            return f"Error: Item {i} missing 'product_id'"
        if "quantity" not in item:
            return f"Error: Item {i} missing 'quantity'"
        if item["quantity"] <= 0:
            return f"Error: Item {i} quantity must be > 0"
    
    # Edge case: Invalid shipping address
    required_fields = ["street", "city", "zip", "country"]
    for field in required_fields:
        if field not in shipping_address or not shipping_address[field]:
            return f"Error: Shipping address missing '{field}'"
    
    # Mock order creation
    order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    total_items = sum(item["quantity"] for item in items)
    
    return (
        f"Order created successfully!\n"
        f"Order ID: {order_id}\n"
        f"Customer: {customer_id}\n"
        f"Items: {total_items}\n"
        f"Shipping to: {shipping_address['city']}, {shipping_address['country']}\n"
        f"Payment: {payment_method}"
    )


@tool
async def calculate_shipping(
    items: List[Dict[str, Any]],
    destination: str,
    shipping_type: str = "standard"
) -> str:
    """
    Calculate shipping cost for order items.
    
    Args:
        items: List of items with 'product_id' and 'quantity'
        destination: Destination country/city
        shipping_type: standard, express, or overnight (default: standard)
    """
    # Edge case: Empty items
    if not items:
        return "Error: Cannot calculate shipping for empty order"
    
    # Edge case: Invalid shipping type
    valid_types = ["standard", "express", "overnight"]
    if shipping_type not in valid_types:
        return f"Error: Invalid shipping type '{shipping_type}'. Valid: {', '.join(valid_types)}"
    
    # Mock shipping rates
    base_rates = {
        "standard": 5.99,
        "express": 15.99,
        "overnight": 29.99
    }
    
    total_weight = sum(item.get("quantity", 1) * 0.5 for item in items)  # Mock weight calculation
    base_cost = base_rates[shipping_type]
    total_cost = base_cost + (total_weight * 2.0)
    
    return (
        f"Shipping Calculation:\n"
        f"Destination: {destination}\n"
        f"Type: {shipping_type}\n"
        f"Items: {len(items)}\n"
        f"Total Weight: {total_weight:.2f} kg\n"
        f"Cost: ${total_cost:.2f}"
    )


@tool
def get_order_status(order_id: str) -> str:
    """
    Get current status of an order.
    
    Args:
        order_id: Order ID to check
    """
    # Edge case: Empty order ID
    if not order_id or not order_id.strip():
        return "Error: Order ID is required"
    
    # Mock order statuses
    order_statuses = {
        "ORD20241116010000": {"status": "processing", "progress": 30},
        "ORD20241116020000": {"status": "shipped", "progress": 80},
        "ORD20241116030000": {"status": "delivered", "progress": 100},
    }
    
    # Edge case: Order not found
    if order_id not in order_statuses:
        return f"Error: Order '{order_id}' not found"
    
    status_info = order_statuses[order_id]
    return (
        f"Order {order_id}:\n"
        f"Status: {status_info['status'].upper()}\n"
        f"Progress: {status_info['progress']}%"
    )


@tool
async def process_payment(
    order_id: str,
    amount: float,
    payment_method: str,
    card_details: Optional[Dict[str, str]] = None
) -> str:
    """
    Process payment for an order.
    
    Args:
        order_id: Order ID
        amount: Payment amount
        payment_method: credit_card, paypal, or bank_transfer
        card_details: Optional dict with 'card_number', 'expiry', 'cvv' (for credit_card)
    """
    # Edge case: Invalid amount
    if amount <= 0:
        return f"Error: Payment amount must be greater than 0, got {amount}"
    
    # Edge case: Missing card details for credit card
    if payment_method == "credit_card":
        if not card_details:
            return "Error: Card details required for credit card payment"
        required_fields = ["card_number", "expiry", "cvv"]
        for field in required_fields:
            if field not in card_details or not card_details[field]:
                return f"Error: Missing card detail '{field}'"
        
        # Edge case: Invalid card number format
        card_num = card_details["card_number"].replace(" ", "").replace("-", "")
        if not card_num.isdigit() or len(card_num) < 13:
            return "Error: Invalid card number format"
    
    # Mock payment processing
    payment_id = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return (
        f"Payment processed successfully!\n"
        f"Payment ID: {payment_id}\n"
        f"Order ID: {order_id}\n"
        f"Amount: ${amount:.2f}\n"
        f"Method: {payment_method}"
    )


@tool
async def apply_discount(
    order_id: str,
    discount_code: str,
    items: List[Dict[str, Any]]
) -> str:
    """
    Apply discount code to order items.
    
    Args:
        order_id: Order ID
        discount_code: Discount code to apply
        items: List of items in the order
    """
    # Edge case: Empty discount code
    if not discount_code or not discount_code.strip():
        return "Error: Discount code cannot be empty"
    
    # Mock discount codes
    discounts = {
        "SAVE10": {"type": "percentage", "value": 10},
        "SAVE20": {"type": "percentage", "value": 20},
        "FLAT50": {"type": "fixed", "value": 50},
        "INVALID": None,  # Edge case: Invalid code
    }
    
    # Edge case: Invalid discount code
    if discount_code not in discounts or discounts[discount_code] is None:
        return f"Error: Invalid discount code '{discount_code}'"
    
    discount = discounts[discount_code]
    
    # Edge case: Empty items
    if not items:
        return "Error: Cannot apply discount to empty order"
    
    # Calculate discount
    total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    
    if discount["type"] == "percentage":
        discount_amount = total * (discount["value"] / 100)
    else:
        discount_amount = min(discount["value"], total)
    
    final_total = total - discount_amount
    
    return (
        f"Discount applied!\n"
        f"Code: {discount_code}\n"
        f"Original Total: ${total:.2f}\n"
        f"Discount: ${discount_amount:.2f}\n"
        f"Final Total: ${final_total:.2f}"
    )


@tool
def validate_customer_info(
    customer_id: str,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> str:
    """
    Validate customer information.
    
    Args:
        customer_id: Customer ID
        email: Optional email address
        phone: Optional phone number
    """
    # Edge case: Empty customer ID
    if not customer_id:
        return "Error: Customer ID is required"
    
    # Edge case: Email validation
    if email:
        if "@" not in email or "." not in email.split("@")[1]:
            return f"Error: Invalid email format: {email}"
    
    # Edge case: Phone validation (simple)
    if phone:
        phone_clean = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        if not phone_clean.isdigit() or len(phone_clean) < 10:
            return f"Error: Invalid phone format: {phone}"
    
    return (
        f"Customer validation successful:\n"
        f"ID: {customer_id}\n"
        f"Email: {email or 'Not provided'}\n"
        f"Phone: {phone or 'Not provided'}"
    )


@tool
async def get_users_from_api(limit: Optional[int] = None) -> str:
    """
    Fetch users from external API (dummyjson.com/users).
    
    Args:
        limit: Optional limit on number of users to return
    """
    if not HAS_AIOHTTP:
        return "Error: aiohttp library not installed. Install with: pip install aiohttp"
    
    try:
        url = "https://dummyjson.com/users"
        if limit:
            url += f"?limit={limit}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    users = data.get("users", [])
                    total = data.get("total", len(users))
                    
                    # Format user list
                    user_list = []
                    for user in users[:limit if limit else len(users)]:
                        user_info = (
                            f"{user.get('firstName', '')} {user.get('lastName', '')} "
                            f"({user.get('email', 'N/A')}) - {user.get('phone', 'N/A')}"
                        )
                        user_list.append(user_info)
                    
                    return (
                        f"Fetched {len(user_list)} users (Total available: {total}):\n"
                        + "\n".join(f"- {user}" for user in user_list)
                    )
                else:
                    return f"Error: API returned status {response.status}"
    except Exception as e:
        return f"Error fetching users: {str(e)}"


async def main():
    """Run complex e-commerce agent example."""
    
    print("=== Complex E-Commerce Agent Example ===\n")
    
    # Create complex e-commerce agent
    ecommerce_agent = Agent(
        id="ecommerce-agent",
        name="E-Commerce Agent",
        description="Comprehensive e-commerce agent handling product search, orders, payments, shipping, and customer support with extensive edge case handling",
        instructions=(
            'You are a helpful e-commerce assistant. '
            'Help customers with product searches, order creation, payment processing, shipping calculations, and order tracking. '
            'Always validate inputs and handle edge cases gracefully. '
            'When searching products, use search_products. '
            'Before creating orders, check inventory with check_inventory. '
            'For orders, use create_order with proper item structure. '
            'Calculate shipping with calculate_shipping. '
            'Process payments with process_payment. '
            'Check order status with get_order_status. '
            'Apply discounts with apply_discount. '
            'Validate customer info with validate_customer_info. '
            'Handle errors gracefully and provide clear feedback.'
        ),
        model={
            "provider": "google",
            "model": "gemini-2.5-flash",
            "api_key": os.getenv("GOOGLE_API_KEY")  # Set GOOGLE_API_KEY in .env file
        },
        tools=[
            search_products,
            check_inventory,
            create_order,
            calculate_shipping,
            get_order_status,
            process_payment,
            apply_discount,
            validate_customer_info,
            get_users_from_api
        ]
    )
    
    print(f"Created agent: {ecommerce_agent}\n")
    
    await ecommerce_agent.startup()
    
    # Test queries covering various edge cases
    test_queries = [
        # Basic search
        "Search for laptops",
        # Search with filters
        "Find phones under $900",
        # Edge case: Empty search
        "Search for products",
        # Inventory check
        "Check if product LAP001 has 3 units in stock",
        # Edge case: Invalid product
        "Check inventory for product INVALID123",
        # Complex order creation
        "Create an order for customer CUST001 with 2 units of LAP001 and 1 unit of PHN001, shipping to 123 Main St, San Francisco, 94102, USA",
        # Edge case: Order with out of stock item
        "Create an order with product LAP003 which is out of stock",
        # Shipping calculation
        "Calculate shipping cost for 2 laptops to New York with express shipping",
        # Payment processing
        "Process payment of $2999.98 for order ORD20241116010000 using credit card",
        # Edge case: Invalid payment amount
        "Process payment of -100 dollars",
        # Discount application
        "Apply discount code SAVE10 to my order",
        # Edge case: Invalid discount code
        "Apply discount code INVALIDCODE",
        # Order status check
        "What's the status of order ORD20241116010000?",
        # Edge case: Non-existent order
        "Check status of order ORD99999999",
        # Customer validation
        "Validate customer CUST001 with email test@example.com and phone 555-1234",
        # Edge case: Invalid email
        "Validate customer CUST002 with email invalid-email",
        # External API call
        "Get all users from the API",
        "Fetch 5 users from the API",
    ]
    
    responses = []
    
    # Rate limiting: Free tier allows 10 requests per minute
    # Add delay after every 6 calls to avoid hitting the limit
    api_call_count = 0
    DELAY_AFTER_N_CALLS = 5
    DELAY_SECONDS = 60
    
    # Use streaming for all tests to demonstrate real-time output
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print('='*60)
        
        # Rate limiting: Add delay after every N calls
        if api_call_count > 0 and api_call_count % DELAY_AFTER_N_CALLS == 0:
            print(f"⏳ Rate limit protection: Waiting {DELAY_SECONDS} seconds after {api_call_count} API calls...")
            await asyncio.sleep(DELAY_SECONDS)
            print("✅ Resuming tests...\n")
        
        print("📡 Streaming response...\n")
        
        try:
            streamed_content = []
            tool_calls = []
            usage = {}
            metadata = {}
            
            # Stream the response and print chunks as they arrive
            async for chunk in ecommerce_agent.stream(query):
                # Print content chunks in real-time
                if chunk.get('content'):
                    content = chunk['content']
                    streamed_content.append(content)
                    print(content, end='', flush=True)
                
                # Collect tool calls, usage, metadata from chunks
                if chunk.get('tool_calls'):
                    tool_calls = chunk.get('tool_calls', [])
                if chunk.get('usage'):
                    usage = chunk.get('usage', {})
                if chunk.get('metadata'):
                    metadata = chunk.get('metadata', {})
            
            print("\n")  # New line after streaming completes
            
            # Increment API call counter (each stream() call counts as one API call)
            api_call_count += 1
            
            # Combine streamed chunks into full response
            full_content = ''.join(streamed_content)
            response = {
                "content": full_content,
                "tool_calls": tool_calls,
                "usage": usage,
                "metadata": metadata,
                "method": "stream"
            }
            
            responses.append({
                "test_number": i,
                "query": query,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
        except Exception as e:
            # Still increment counter even on error (API call was made)
            api_call_count += 1
            
            # Check if it's a rate limit error
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                print(f"\n⚠️  Rate limit error detected!")
                print(f"⏳ Waiting {DELAY_SECONDS} seconds before retrying...")
                await asyncio.sleep(DELAY_SECONDS)
                print("✅ Retrying...\n")
                
                # Retry the query once
                try:
                    streamed_content = []
                    tool_calls = []
                    usage = {}
                    metadata = {}
                    
                    async for chunk in ecommerce_agent.stream(query):
                        if chunk.get('content'):
                            content = chunk['content']
                            streamed_content.append(content)
                            print(content, end='', flush=True)
                        if chunk.get('tool_calls'):
                            tool_calls = chunk.get('tool_calls', [])
                        if chunk.get('usage'):
                            usage = chunk.get('usage', {})
                        if chunk.get('metadata'):
                            metadata = chunk.get('metadata', {})
                    
                    print("\n")
                    api_call_count += 1
                    
                    full_content = ''.join(streamed_content)
                    response = {
                        "content": full_content,
                        "tool_calls": tool_calls,
                        "usage": usage,
                        "metadata": metadata,
                        "method": "stream"
                    }
                    
                    responses.append({
                        "test_number": i,
                        "query": query,
                        "response": response,
                        "timestamp": datetime.now().isoformat(),
                        "success": True
                    })
                    continue  # Skip the error handling below
                except Exception as retry_error:
                    print(f"\n❌ Retry also failed: {str(retry_error)}\n")
            
            print(f"\n❌ Error: {str(e)}\n")
            responses.append({
                "test_number": i,
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "method": "stream"
            })
    
    # Save comprehensive results
    output_file = Path(__file__).parent.parent / "jsons" / "complex_ecommerce_agent_responses.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            "agent_id": ecommerce_agent.id,
            "agent_name": ecommerce_agent.name,
            "total_tests": len(test_queries),
            "successful_tests": sum(1 for r in responses if r.get("success", False)),
            "failed_tests": sum(1 for r in responses if not r.get("success", False)),
            "timestamp": datetime.now().isoformat(),
            "test_results": responses
        }, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print(f"💾 Test results saved to: {output_file}")
    print(f"📊 Summary: {sum(1 for r in responses if r.get('success', False))}/{len(responses)} tests passed")
    print('='*60)
    
    await ecommerce_agent.shutdown()
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

