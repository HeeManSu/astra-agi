from .committee_chair import committee_chair
from .devils_advocate import devils_advocate
from .financial_analyst import financial_analyst
from .macro_strategist import macro_strategist
from .portfolio_manager import portfolio_manager
from .risk_officer import risk_officer
from .technical_analyst import technical_analyst
from .valuation_analyst import valuation_analyst


ALL_AGENTS = [
    # Research Layer
    macro_strategist,
    financial_analyst,
    valuation_analyst,
    technical_analyst,
    # Governance Layer
    devils_advocate,
    risk_officer,
    portfolio_manager,
    committee_chair,
]
