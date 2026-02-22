from .committee_chair import committee_chair
from .financial_analyst import financial_analyst
from .knowledge_agent import knowledge_agent
from .market_analyst import market_analyst
from .memo_writer import memo_writer
from .risk_officer import risk_officer
from .technical_analyst import technical_analyst


ALL_AGENTS = [
    market_analyst,
    financial_analyst,
    technical_analyst,
    risk_officer,
    knowledge_agent,
    memo_writer,
    committee_chair,
]
