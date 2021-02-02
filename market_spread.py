from decimal import Decimal

__all__ = ['get_spread']

def get_spread(market1, market2, depth=Decimal(0)):
    """
    Returns tuple containing: M1 WA ask minus M2 WA bid and M2 WA ask minus M1
    WA bid for a given depth. M1 = market 1, M2 = market,WA = weighted average 
    """

    