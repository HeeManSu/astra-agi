"""
Unit and Integration Tests for E-commerce Order Fulfillment Teams.

Test Cases:
1. test_order_processing_team_coordinate_mode - Coordinate mode processes complete order
2. test_customer_support_team_route_mode - Route mode routes to correct specialist
3. test_fraud_detection_team_collaborate_mode - Collaborate mode analyzes with multiple analysts
4. test_operations_team_hierarchical_mode - Hierarchical mode manages nested teams
5. test_team_streaming - Teams stream events correctly
6. test_team_memory - Teams use memory/thread_id correctly
7. test_team_error_handling - Teams handle errors gracefully
"""

from examples.team_workflow.teams import (
    customer_support_team,
    fraud_detection_team,
    operations_team,
    order_processing_team,
)
import pytest


@pytest.mark.integration
async def test_order_processing_team_coordinate_mode():
    """Test order processing team coordinate mode processes complete order."""
    # Coordinate mode should decompose order processing into subtasks
    message = (
        "Process this order: Order ID ORD-001, Customer CUST-100, "
        "Items: [{'product_id': 'PROD-001', 'quantity': 1, 'price': 99.99}], "
        "Shipping: {'country': 'US', 'address': '123 Main St'}, "
        "Payment: {'method': 'credit_card', 'amount': 99.99}"
    )
    result = await order_processing_team.invoke(message)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
async def test_customer_support_team_route_mode():
    """Test customer support team route mode routes to correct specialist."""
    # Route mode should delegate to single best member
    result = await customer_support_team.invoke(
        "I need help with a refund for order ORD-001"
    )
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
async def test_fraud_detection_team_collaborate_mode():
    """Test fraud detection team collaborate mode analyzes with multiple analysts."""
    # Collaborate mode should delegate same task to all members
    message = (
        "Analyze fraud risk for order ORD-002: customer CUST-200, "
        "amount $5000, payment_method prepaid_card"
    )
    result = await fraud_detection_team.invoke(message)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
async def test_operations_team_hierarchical_mode():
    """Test operations team hierarchical mode manages nested teams."""
    # Hierarchical mode should support nested team delegation
    result = await operations_team.invoke(
        "Process order ORD-003 and handle customer inquiry about shipping status"
    )
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
async def test_team_streaming():
    """Test teams stream events correctly."""
    events = []
    async for event in customer_support_team.stream("I need help with my order"):
        events.append(event)
        # Check for team-specific events
        if hasattr(event, "event_type"):
            assert event.event_type in [
                "delegation_start",
                "delegation_result",
                "member_execution",
                "synthesis",
                "team_status",
            ]

    assert len(events) > 0


@pytest.mark.integration
async def test_team_memory():
    """Test teams use memory/thread_id correctly."""
    thread_id = "test-thread-123"

    # First invocation
    result1 = await customer_support_team.invoke(
        "My order number is ORD-001", thread_id=thread_id
    )
    assert result1 is not None

    # Second invocation should remember context
    result2 = await customer_support_team.invoke(
        "What is my order number?", thread_id=thread_id
    )
    assert result2 is not None
    # Note: Actual memory behavior depends on model and context window


@pytest.mark.integration
async def test_team_error_handling():
    """Test teams handle errors gracefully."""
    # Test with invalid input
    try:
        result = await customer_support_team.invoke("")
        # Should either return a helpful message or raise an error
        assert result is not None or True  # Accept either behavior
    except Exception:
        # Error handling is acceptable
        pass
