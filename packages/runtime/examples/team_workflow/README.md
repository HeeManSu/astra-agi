# E-commerce Order Fulfillment - Production Example

## Overview

Production-grade example demonstrating all team execution modes with a **realistic e-commerce order fulfillment workflow**. This example showcases how multiple specialized agents coordinate to process orders from validation to shipping.

This example demonstrates:

- **Route Mode**: Customer support routing to appropriate specialists
- **Coordinate Mode**: Complete order processing workflow (validate → inventory → payment → shipping)
- **Collaborate Mode**: Multiple fraud analysts reviewing the same order
- **Hierarchical Mode**: Operations team managing nested fulfillment teams

## Real-World Use Case

This example simulates a real e-commerce order fulfillment system where:

1. **Orders are validated** for completeness and business rules
2. **Inventory is checked and reserved** for confirmed orders
3. **Payments are processed** through payment gateways
4. **Shipping is calculated and labels are generated**
5. **Customers are notified** at each stage
6. **Fraud detection** analyzes orders for risk

## Directory Structure

```
packages/runtime/examples/team_workflow/
├── __init__.py
├── main.py                    # Server setup with teams
├── README.md                  # This file
├── api_client.py              # Backend API testing client
├── agents/                    # Individual agent definitions
│   ├── __init__.py
│   ├── order_validator_agent.py
│   ├── inventory_agent.py
│   ├── payment_agent.py
│   ├── shipping_agent.py
│   ├── customer_service_agent.py
│   └── fraud_detection_agent.py
├── teams/                     # Team definitions
│   ├── __init__.py
│   ├── order_processing_team.py    # Coordinate mode
│   ├── customer_support_team.py    # Route mode
│   ├── fraud_detection_team.py     # Collaborate mode
│   └── operations_team.py          # Hierarchical mode
├── tools/                     # Tools organized by agent
│   ├── __init__.py
│   ├── order_validator/
│   ├── inventory_agent/
│   ├── payment_agent/
│   ├── shipping_agent/
│   ├── customer_service/
│   └── fraud_detection/
├── middlewares/               # Custom middlewares
├── guardrails/                # Custom guardrails
├── db/                        # Database setup
└── tests/                     # Test cases
    ├── __init__.py
    └── test_teams.py
```

## Agents

### Order Validator Agent

**Purpose**: Validates order details, customer information, and order requirements

**Tools**:

- `validate_order()` - Validates order details, customer info, shipping address

**Use Case**: First step in order processing to ensure orders meet business rules

**Example**:

```python
result = await order_validator_agent.invoke(
    "Validate this order: Order ID ORD-123, Customer CUST-456, "
    "Items: [{'product_id': 'PROD-001', 'quantity': 2, 'price': 99.99}], "
    "Shipping: {'country': 'US', 'address': '123 Main St'}"
)
```

### Inventory Agent

**Purpose**: Checks stock availability and reserves items for orders

**Tools**:

- `check_inventory()` - Checks stock availability for products
- `reserve_items()` - Reserves items in inventory for an order

**Use Case**: Ensures products are available before processing payment

**Example**:

```python
result = await inventory_agent.invoke(
    "Check inventory for products PROD-001, PROD-002 and reserve 2 units "
    "of PROD-001 for order ORD-123"
)
```

### Payment Agent

**Purpose**: Processes payments and handles refunds

**Tools**:

- `process_payment()` - **Async** - Processes payment through payment gateway
- `refund_payment()` - **Async** - Processes refunds for orders

**Use Case**: Handles all financial transactions for orders

**Example**:

```python
result = await payment_agent.invoke(
    "Process payment for order ORD-123: amount $199.98, "
    "payment_method credit_card, customer CUST-456"
)
```

### Shipping Agent

**Purpose**: Calculates shipping costs and generates shipping labels

**Tools**:

- `calculate_shipping()` - **Async** - Calculates shipping costs and delivery estimates
- `generate_label()` - **Async** - Generates shipping labels

**Use Case**: Handles shipping logistics after payment confirmation

**Example**:

```python
result = await shipping_agent.invoke(
    "Calculate shipping for order ORD-123: destination US, weight 2.5kg, "
    "method express, then generate shipping label"
)
```

### Customer Service Agent

**Purpose**: Sends notifications and updates order status

**Tools**:

- `send_notification()` - **Async** - Sends email/SMS notifications to customers
- `update_order_status()` - Updates order status in the system

**Use Case**: Keeps customers informed throughout the order process

**Example**:

```python
result = await customer_service_agent.invoke(
    "Send order confirmation notification to customer CUST-456 for order ORD-123"
)
```

### Fraud Detection Agent

**Purpose**: Analyzes orders for potential fraud indicators

**Tools**:

- `check_fraud_risk()` - **Async** - Analyzes order for fraud risk

**Use Case**: Identifies potentially fraudulent orders before processing

**Example**:

```python
result = await fraud_detection_agent.invoke(
    "Check fraud risk for order ORD-123: customer CUST-456, amount $199.98, "
    "payment_method credit_card"
)
```

## Teams

### Order Processing Team (Coordinate Mode)

**Purpose**: Coordinates complete order fulfillment workflow

**Execution Mode**: `coordinate`

**Members**:

- `order-validator-agent`: Validates order details
- `inventory-agent`: Checks stock and reserves items
- `payment-agent`: Processes payment
- `shipping-agent`: Calculates shipping and generates label
- `customer-service-agent`: Sends notifications

**Workflow**: Order → Validate → Inventory → Payment → Shipping → Notification

**Use Case**: Complete end-to-end order processing

**Example**:

```python
result = await order_processing_team.invoke(
    "Process this order: Order ID ORD-123, Customer CUST-456, "
    "Items: [{'product_id': 'PROD-001', 'quantity': 2, 'price': 99.99}], "
    "Shipping: {'country': 'US', 'address': '123 Main St'}, "
    "Payment: {'method': 'credit_card', 'amount': 199.98}"
)
# Team decomposes into: validate → inventory → payment → shipping → notify
```

### Customer Support Team (Route Mode)

**Purpose**: Routes customer inquiries to the appropriate specialist

**Execution Mode**: `route`

**Members**:

- `customer-service-agent`: General inquiries, order status
- `order-validator-agent`: Order validation questions
- `inventory-agent`: Stock availability questions
- `payment-agent`: Payment issues, refunds
- `shipping-agent`: Shipping costs, delivery times

**Use Case**: Customer support routing

**Example**:

```python
result = await customer_support_team.invoke(
    "I need help with a refund for my order ORD-123"
)
# Routes to payment-agent for refund handling
```

### Fraud Detection Team (Collaborate Mode)

**Purpose**: Multiple fraud analysts review the same order simultaneously

**Execution Mode**: `collaborate`

**Members**:

- `fraud-analyst-1`: Payment method and transaction pattern analysis
- `fraud-analyst-2`: Address verification and geographic risk
- `fraud-analyst-3`: Customer behavior and order value risk

**Use Case**: Comprehensive fraud risk assessment

**Example**:

```python
result = await fraud_detection_team.invoke(
    "Analyze fraud risk for order ORD-123: customer CUST-456, "
    "amount $5000, payment_method prepaid_card, "
    "shipping and billing addresses differ"
)
# All three analysts work on the SAME order, then synthesize perspectives
```

### Operations Team (Hierarchical Mode)

**Purpose**: Manages all order fulfillment operations with nested team structure

**Execution Mode**: `hierarchical`

**Members**:

- `order-processing-team`: Nested team (coordinate mode)
- `customer-support-team`: Nested team (route mode)
- `fraud-detection-team`: Nested team (collaborate mode)
- `operations-manager-agent`: Direct agent for strategic decisions

**Use Case**: Multi-level organizational structure

**Example**:

```python
result = await operations_team.invoke(
    "Process order ORD-123 and handle customer inquiry about order status"
)
# Delegates to order-processing-team and customer-support-team, which further delegate
```

## Running the Example

### Prerequisites

```bash
# Install dependencies
cd packages/runtime
uv sync

# Set environment variables
export MONGODB_URL=mongodb://localhost:27017
export ASTRA_JWT_SECRET=dev-secret-for-testing
```

### Start the Server

```bash
cd packages/runtime
uv run --package astra-runtime python examples/team_workflow/main.py
```

### Access Points

- **API Docs**: http://127.0.0.1:8000/docs
- **Playground Teams**: http://127.0.0.1:8000/api/v1/teams
- **Playground UI**: http://127.0.0.1:8000/

## API Usage

### List Teams

```bash
curl http://localhost:8000/api/v1/teams
```

### Get Team Details

```bash
curl http://localhost:8000/api/v1/teams/order-processing-team
```

### Generate Team Response

```bash
curl -X POST http://localhost:8000/api/v1/teams/order-processing-team/generate \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process this order: Order ID ORD-123, Customer CUST-456, Items: [{\"product_id\": \"PROD-001\", \"quantity\": 2, \"price\": 99.99}], Shipping: {\"country\": \"US\"}, Payment: {\"method\": \"credit_card\", \"amount\": 199.98}"
  }'
```

### Stream Team Response

```bash
curl -X POST http://localhost:8000/api/v1/teams/order-processing-team/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process order ORD-123..."
  }' \
  --no-buffer
```

## Real-World Scenarios

### Scenario 1: Complete Order Processing

**Use**: `order_processing_team` (Coordinate Mode)

**Request**:

```
Process this order:
- Order ID: ORD-001
- Customer: CUST-100
- Items: [{"product_id": "PROD-001", "quantity": 1, "price": 99.99}]
- Shipping: {"country": "US", "address": "123 Main St, New York, NY 10001"}
- Payment: {"method": "credit_card", "amount": 99.99}
```

**What Happens**:

1. Order Validator validates order details
2. Inventory Agent checks stock and reserves item
3. Payment Agent processes payment
4. Shipping Agent calculates shipping and generates label
5. Customer Service sends confirmation notification
6. Team synthesizes final order confirmation

### Scenario 2: Customer Support Inquiry

**Use**: `customer_support_team` (Route Mode)

**Request**:

```
"I need help with a refund for order ORD-001"
```

**What Happens**:

1. Team leader analyzes request
2. Routes to Payment Agent (best specialist for refunds)
3. Payment Agent handles refund request
4. Response returned directly

### Scenario 3: High-Value Order Fraud Check

**Use**: `fraud_detection_team` (Collaborate Mode)

**Request**:

```
Analyze fraud risk for order ORD-002:
- Customer: CUST-200
- Amount: $5000
- Payment: prepaid_card
- Shipping and billing addresses differ
```

**What Happens**:

1. All three fraud analysts analyze the SAME order simultaneously
2. Analyst 1: Checks payment method risk
3. Analyst 2: Checks address mismatch risk
4. Analyst 3: Checks order value risk
5. Team synthesizes all perspectives into unified risk assessment

### Scenario 4: Complex Operations Request

**Use**: `operations_team` (Hierarchical Mode)

**Request**:

```
Process order ORD-003 and handle customer inquiry about shipping status
```

**What Happens**:

1. Operations team delegates to order-processing-team
2. Operations team delegates to customer-support-team
3. Order-processing-team further delegates to its members
4. Customer-support-team routes to shipping-agent
5. Operations team synthesizes results from both teams

## Async Tools

Several tools use async operations to simulate real-world API interactions:

- **`process_payment()`** - Simulates payment gateway delay (0.5s)
- **`refund_payment()`** - Simulates refund processing delay (0.4s)
- **`calculate_shipping()`** - Simulates shipping API delay (async)
- **`generate_label()`** - Simulates label generation delay (0.6s)
- **`send_notification()`** - Simulates email/SMS service delay (0.3s)
- **`check_fraud_risk()`** - Simulates fraud analysis delay (0.7s)

These async operations demonstrate how teams handle real-world I/O-bound tasks.

## Testing

### Run Unit/Integration Tests

```bash
cd packages/runtime
uv run pytest examples/team_workflow/tests/ -v
```

## Key Differences: Execution Modes

### Route Mode

- **Task Distribution**: Single task to single best member
- **Execution**: One delegation, direct return
- **Use Case**: Simple routing (customer support)

### Coordinate Mode

- **Task Distribution**: Decompose into different subtasks
- **Execution**: Multiple delegations, sequential or parallel
- **Use Case**: Multi-step workflows (order processing)

### Collaborate Mode

- **Task Distribution**: Same task to all members
- **Execution**: All members work simultaneously
- **Use Case**: Multi-perspective analysis (fraud detection)

### Hierarchical Mode

- **Task Distribution**: Can delegate to nested teams
- **Execution**: Multi-level delegation with recursion
- **Use Case**: Organizational hierarchies (operations management)

## Notes

- All teams and agents share the same MongoDB storage instance
- Async tools simulate real-world API delays
- Tools use mock data stores (in production, these would be real databases)
- Memory integration works with `thread_id` for conversation continuity
- Streaming supports all team-specific events (delegation_start, delegation_result, etc.)
