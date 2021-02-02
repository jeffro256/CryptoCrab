""" Weighted Average Price tool """

from decimal import Decimal
import market as market_

# Returns the weighted average price for a certain depth into the bids book
# Parameters:
#	 market - The market in question
#	 depth  - A Decimal representing the value of depth in base currency
#	 side   - Side of market: Market.BID or Market.ASK
#	 curr   - Param depth currency type: Market.BASE_CURR or Market.QUOTE_CURR
def wap(market, depth, side, curr=market_.BASE_CURR):
	sum_price = Decimal(0)
	sum_size = Decimal(0)

	orders = market.bids() if side == market_.BID else market.asks()

	for order in orders:
		price = order[0]
		order_size = order[1] * (price if curr == market_.QUOTE_CURR else 1)
		size = min(order_size, depth - sum_size)

		sum_price += price * size
		sum_size += size

		if sum_size >= depth:
			break

	wap = (sum_price / sum_size).quantize(market.tick_size())

	return wap