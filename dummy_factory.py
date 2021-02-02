from decimal import Decimal
from market import DummyMarket
from tickers import *

__all__ = ['dummy_factory', 'test_dummies']

def dummy_factory(pair, name=None, symbol=None, exchange=None, ts=None, ss=None, \
	bids=None, asks=None, lm=None):
	name = name or 'Dummy {}/{}'.format(*pair)
	symbol = symbol or '{}-{}'.format(*pair)
	exchange = exchange or 'BitDummy'
	tick_size = ts or Decimal('0.01')
	step_size = ss or Decimal('0.00000001')
	bids = bids or [[Decimal('100'), Decimal('10')]]
	asks = asks or [[Decimal('110'), Decimal('10')]]
	last_match = lm or Decimal('1000')

	dummy = DummyMarket(name, pair, symbol, exchange, tick_size, step_size, bids, asks, last_match)

	return dummy

_test_pairs = [(BTC, USD), (ETH, BTC), (ETH, KRW), (XRP, KRW), (XRP, ETH), (ETH, USD)]
test_dummies = list(map(dummy_factory, _test_pairs))
test_dummies += list(map(lambda x: dummy_factory(x, exchange='Dumbhumb'), _test_pairs))