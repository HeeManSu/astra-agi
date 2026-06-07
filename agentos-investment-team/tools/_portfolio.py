"""
Shared portfolio state reader.

Used by both risk_tools.py and portfolio_tools.py.
Reads from portfolio.json in the project root.
"""

from __future__ import annotations

import json
from pathlib import Path


PORTFOLIO_PATH = Path(__file__).resolve().parent.parent / "portfolio.json"


def load_portfolio() -> dict:
    """Load portfolio state from JSON file."""
    if not PORTFOLIO_PATH.exists():
        return {
            "error": f"Portfolio file not found at {PORTFOLIO_PATH}",
            "nav": 0,
            "cash": 0,
            "positions": [],
        }
    with open(PORTFOLIO_PATH) as f:
        return json.load(f)


def get_holdings() -> list[dict]:
    """Return list of position dicts."""
    return load_portfolio().get("positions", [])


def get_cash() -> float:
    """Return available cash."""
    return float(load_portfolio().get("cash", 0))


def get_nav() -> float:
    """Return total NAV."""
    return float(load_portfolio().get("nav", 0))
