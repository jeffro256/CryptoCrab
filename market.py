__all__ = ['Market', 'BasicMarket', 'DummyMarket', 'BUY', 'SELL', 'BID', 'ASK',
	'BASE_CURR', 'QUOTE_CURR']

BUY = 'BUY'
SELL = 'SELL'
BID = 'BID'
ASK = 'ASK'
BASE_CURR = 'BASE'
QUOTE_CURR = 'QUOTE'

""" A general class to represent an abstract market.
	All numbers should be represented by the decimal.Decimal class
"""
class Market(object):
	""" Returns the display name of the market """
	def disp_name(self):
		raise NotImplementedError("Method 'disp_name' from class 'Market' not implemented")

	""" Returns a tuple of two ticker strings representing the market pair 
		Result looks like this: ( ticker1, ticker2 )
		The tickers are defined in tickers.py
		Here ticker 1 is the "base" currency and ticker2 is the "quote" currency
	"""
	def pair(self):
		raise NotImplementedError("Method 'pair' from class 'Market' not implemented")

	""" Returns the exchange-specific market symbol """
	def symbol(self):
		raise NotImplementedError("Method 'symbol' from class 'Market' not implemented")

	""" Returns the name of the exchange """
	def exchange(self):
		raise NotImplementedError("Method 'exchange' from class 'Market' not implemented")

	""" Return of list of bids, sorted best to worst in this format: 
		[
			[ price_1, volume_1 ],
			[ price_2, volume_2 ],
			...
			[ price_n, volume_n ],
		]

		where volumes are in the base currency
	"""
	def bids(self):
		raise NotImplementedError("Method 'bids' from class 'Market' not implemented")

	""" Return of list of asks, sorted best to worst in this format: 
		[
			[ price_1, volume_1 ],
			[ price_2, volume_2 ],
			...
			[ price_n, volume_n ],
		]

		where volumes are in the base currency
	"""
	def asks(self):
		raise NotImplementedError("Method 'asks' from class 'Market' not implemented")

	""" Return best bid """
	def best_bid(self):
		raise NotImplementedError("Method 'best_bid' from class 'Market' not implemented")

	""" Return best ask """
	def best_ask(self):
		raise NotImplementedError("Method 'best_ask' from class 'Market' not implemented")

	""" Return the last trade price, or None if no data """
	def last_match(self):
		raise NotImplementedError("Method 'last_match' from class 'Market' not implemented")

	""" Return the smallest number the price can be quantized to 
		If not available, return None
	"""
	def tick_size(self):
		raise NotImplementedError("Method 'tick_size' from class 'Market' not implemented")

	""" Return the smallest number the size can be quantized to
		If not available, return None
	"""
	def step_size(self):
		raise NotImplementedError("Method 'step_size' from class 'Market' not implemented")

	""" Returns a boolean value indicating whether or not the market is active """
	def is_active(self):
		raise NotImplementedError("Method 'is_active' from class 'Market' not implemented")		

	""" Should return datetime of time data was last updated. Return None if no data """
	def last_updated(self):
		raise NotImplementedError("Method 'last_updated' from class 'Market' not implemented")

	""" Non-Abstract Methods """

	""" Default constructor """
	def __init__(self):
		self._lock = threading.RLock()

	""" 
		Equivalent to calling .acquire() on an internal RLock.
		The point of the lock is to update market data thread-safely
	"""
	def lock(self, blocking=True, timeout=-1):
		return self._lock.acquire(blocking, timeout)

	""" Equivalent to calling .acquire() on an internal RLock """
	def unlock(self):
		return self._lock.release()

	"""
		Returns the depth of the bid side of the market.
		'quote_asset' paramter specifiies whether to count in the base or quote asset
	"""
	def bid_depth(self, quote_asset=False):
		self.lock()
		bids = self.bids()
		s = sum((b[0] * b[1] for b in bids) if quote_asset else (b[0] for b in bids))
		self.unlock()

		return s

	"""
		Returns the depth of the ask side of the market.
		'quote_asset' paramter specifiies whether to count in the base or quote asset
	"""
	def ask_depth(self, quote_asset=False):
		self.lock()
		asks = self.asks()
		s = sum((a[0] * a[1] for a in asks) if quote_asset else (a[0] for a in asks))
		self.unlock()

		return s

	""" Returns whether two market are equal. It checks the exchange and the pair """
	def __eq__(self, other):
		return self.exchange() == other.exchange() and self.pair() == other.pair()

	""" Returns a default string for the market """
	def __str__(self):
		return '{}({})'.format(self.exchange(), self.disp_name())

import copy
import datetime
import threading

""" A Basic Market Implementation """
class BasicMarket(Market):
	""" The bids and asks are dictionaries in this format: 
		{
			price_1: size_1,
			price_2: size_2,
			... 
			price_n: size_n,
		}
	"""
	def __init__(self, name, pair, symbol, exchange, tick_size, step_size):
		super().__init__()

		self._name = name
		self._pair = pair
		self._symbol = symbol
		self._exchange = exchange
		self._tick_size = tick_size
		self._step_size = step_size
		self._bids = {}
		self._asks = {}
		self._last_match_price = None
		self._utime = None
		self._active = False

	""" Market Interface Methods """

	def disp_name(self):
		return self._name

	def pair(self):
		return self._pair

	def symbol(self):
		return self._symbol

	def exchange(self):
		return self._exchange

	def bids(self):
		self.lock()
		bids = [[x, self._bids[x]] for x in sorted(self._bids.keys(), reverse=True)]
		self.unlock()

		return bids

	def asks(self):
		self.lock()
		asks = [[x, self._asks[x]] for x in sorted(self._asks.keys())]
		self.unlock()

		return asks

	def best_bid(self):
		self.lock()
		best = max(self._bids.keys()) if self._bids else None
		self.unlock()

		return best

	def best_ask(self):
		self.lock()
		best = min(self._asks.keys()) if self._asks else None
		self.unlock()

		return best

	def last_match(self):
		return self._last_match_price

	def tick_size(self):
		return self._tick_size

	def step_size(self):
		return self._step_size

	def is_active(self):
		return self._active

	def last_updated(self):
		return self._utime

	""" Implementation Methods """

	def clear(self, utime=None):
		self.lock()

		self._bids.clear()
		self._asks.clear()
		self._last_match_price = None
		self._utime = utime or datetime.datetime.now()

		self.unlock()

	def update_bid(self, price, size, utime=None):
		self.lock()

		if size == 0:
			if price in self._bids:
				del self._bids[price]
		else:
			self._bids[price] = size

		self._utime = utime or datetime.datetime.now()

		self.unlock()

	def update_ask(self, price, size, utime=None):
		self.lock()

		if size == 0:
			if price in self._asks:
				del self._asks[price]
		else:
			self._asks[price] = size

		self._utime = utime or datetime.datetime.now()

		self.unlock()

	def reset_book(self, bids, asks, last_match_price=None, utime=None):
		self.lock()

		self._bids = bids
		self._asks = asks
		self._last_match_price = last_match_price
		self._utime = utime or datetime.datetime.now()

		self.unlock()

	def match(self, last_match_price, utime=None):
		self.lock()

		self._last_match_price = last_match_price
		self._utime = utime or datetime.datetime.now()

		self.unlock()

	def set_active(self, active):
		self._active = active

""" A market that isn't connected to anything, used for examples """ 
class DummyMarket(Market):
	def __init__(self, name, pair, symbol, exchange, tick_size, step_size, bids, asks, last_match):
		super().__init__()

		self._name = name
		self._pair = pair
		self._symbol = symbol
		self._exchange = exchange
		self._tick_size = tick_size
		self._step_size = step_size
		self._bids = bids
		self._asks = asks
		self._last_match_price = last_match

	""" Market Interface Methods """

	def disp_name(self):
		return self._name

	def pair(self):
		return self._pair

	def symbol(self):
		return self._symbol

	def exchange(self):
		return self._exchange

	def bids(self):
		self._bids.sort(reverse=True)
		return self._bids

	def asks(self):
		self._asks.sort()
		return self._asks

	def best_bid(self):
		self._bids.sort(reverse=True)
		return self._bids[0] if self._bids else None

	def best_ask(self):
		self._asks.sort()
		return self._asks[0] if self._asks else None

	def last_match(self):
		return self._last_match_price

	def tick_size(self):
		return self._tick_size

	def step_size(self):
		return self._step_size

	def is_active(self):
		return False

	def last_updated(self):
		return datetime.datetime.now()
