from enum import Enum

class PortfolioType(Enum):
    HONG = "HONG"
    LAB = "LAB"

def validate_portfolio_id(portfolio_id: str) -> bool:
    """Validate format of portfolio_id"""
    return len(portfolio_id) > 0

def is_hong_portfolio(portfolio_id: str) -> bool:
    # Convention: HONG portfolios start with 'hong_' or are exactly 'hong'
    return portfolio_id.lower().startswith("hong")
