from astra import tool


@tool
def get_stock_price(symbol: str) -> str:
    """Get the current stock price for a symbol."""
    return f"{symbol}: $150.00"
