from decimal import Decimal
import json
import time
from urllib.request import urlopen

import ccpysher
from exchange_client import ExchangeClient
import exchanges
import market
from tickers import *
from tools import first

__all__ = ['BitstampClient']

class BitstampClient(ExchangeClient):
	def __init__(self):
		self._markets = {}
		self._pairs = []
		self._did_recieve = {}

		appkey = 'de504dc5763aeef9ff52'
		self._pusher = ccpysher.Pusher(appkey)
		self._pusher.connection.bind('pusher:connection_established', self._connect_handle)
		self._pusher.connection.bind('pusher:connection_failed', self._failed_handle)
		self._pusher.connection.bind_time_out(self._time_out_handle)

	def get_pairs(self):
		return self._pairs

	def set_pairs(self, pairs):
		self._pairs = pairs

		#TODO: add input validation

	def start(self):
		if not self._pairs:
			print("Warning: Pairs not set for Bitstamp client!")
			return

		bitstamp_info_url = 'https://www.bitstamp.net/api/v2/trading-pairs-info/'
		bitstamp_info = json.loads(urlopen(bitstamp_info_url).read().decode())

		exchange = exchanges.BitstampExchange.instance()

		for pair in self._pairs:
			symbol = ''.join(pair).lower()
			pair_info = first(bitstamp_info, lambda i: i['url_symbol'] == symbol)
			name = pair_info['name']
			tick_size = Decimal('0.1') ** Decimal(pair_info['counter_decimals'])
			step_size = Decimal('0.1') ** Decimal(pair_info['base_decimals'])

			market_ = market.BasicMarket(name, pair, symbol, exchange, tick_size, step_size)
			self._markets[symbol] = market_

			self._did_recieve[symbol] = False

		self._pusher.connect()

	def stop(self):
		print("Closing Bitstamp client...")

		self._pusher.disconnect()

		for symbol in self._markets:
			self._markets[symbol].set_active(False)

		self._markets.clear()
		self._did_recieve.clear()

	def get_markets(self):
		return list(self._markets.values())

	def _connect_handle(self, data):
		#print("Data: ", data)

		for symbol in self._markets:
			market = self._markets[symbol]
			channel_name = ('order_book_' + symbol) if (symbol != 'btcusd') else 'order_book'
			channel = self._pusher.subscribe(channel_name)
			channel.bind('data', self._create_processor(market))

	def _failed_handle(self, data):
		print("FAILURE! Data: ", data)

	def _time_out_handle(self):
		print("TIME OUT!!!")

	def _create_processor(self, market):
		def _inner(*args, **kwargs):
			obook_data = json.loads(args[0])
			bids_raw = obook_data['bids']
			asks_raw = obook_data['asks']

			bids = {}
			for raw_bid in bids_raw:
				price = Decimal(raw_bid[0]).quantize(market.tick_size())
				size = Decimal(raw_bid[1]).quantize(market.step_size())
				
				bids[price] = size

			asks = {}
			for raw_ask in asks_raw:
				price = Decimal(raw_ask[0]).quantize(market.tick_size())
				size = Decimal(raw_ask[1]).quantize(market.step_size())
				
				asks[price] = size

			market.reset_book(bids, asks)

			e_name = market.exchange().name()
			symbol = market.symbol()
			if not self._did_recieve[symbol]:
				print("Got first", e_name, symbol, "data")

				self._did_recieve[symbol] = True

		return _inner

if __name__ == '__main__':
	cli = BitstampClient()
	cli.set_pairs([(BTC, USD), (LTC, BTC)])
	cli.start()
	markets = cli.get_markets()
	try:
		for i in range(200):
			print("------------------------")
			for market_ in markets:
				print(market_.symbol(), str(market_.best_bid()).ljust(10), str(market_.best_ask()).ljust(10), sep="\t")
			#print(cli._pusher.connection.state)
			time.sleep(5)
	except KeyboardInterrupt:
		print()
	cli.stop()
	print("Goodbye!")
