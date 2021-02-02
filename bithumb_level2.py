from decimal import Decimal
import exchanges
import json
from market import BasicMarket
import socket
from threading import Thread
from tickers import *
from time import sleep, perf_counter as clock # < No morals
from tools import first
import traceback
from urllib.request import urlopen
from urllib.error import URLError

""" Note: Due to the Bithumb API, the markets always seem very shallow 
	because the API allows you to see AT MOST 20 orders deep ;(		 """
class Level2BithumbClient(object):
	def __init__(self, pairs):
		self.pairs = pairs
		self.running = False
		self._thread = None
		self.markets = []

	def start(self):
		if self.running:
			return

		# I looked these tick sizes up myself because there's no way to grab 
		# them programmatically without a web crawler. Subject to change.
		tick_sizes = {
			BITCOIN: Decimal('1000'),
			ETHEREUM: Decimal('100'),
			DASH: Decimal('100'),
			LITECOIN: Decimal('50'),
			ETHEREUM_CLASSIC: Decimal('10'),
			RIPPLE: Decimal('1'),
			BCASH: Decimal('500'),
			MONERO: Decimal('100'),
			ZCASH: Decimal('100'),
			QTUM: Decimal('10'),
			BGOLD: Decimal('100'),
			EOS: Decimal('1')
		}

		self.markets = []
		for pair in self.pairs:
			name = '{}/{}'.format(*pair)
			exchange = exchanges.BithumbExchange.instance()
			symbol = pair[0]
			tick_size = tick_sizes[symbol]
			step_size = Decimal('0.00000001')
			market = BasicMarket(name, pair, symbol, exchange, tick_size, step_size)
			self.markets.append(market)

		if len(self.pairs) >= 20:
			# For Bithumb's 20 requests/second limit
			print("Bithumb pairs over 20, using compact API")

		def _loop():
			base_url = 'https://api.bithumb.com/public/orderbook/'

			old_time = clock()
			while self.running:
				new_time = clock()

				try:
					if (new_time - old_time) > 1.5:
						old_time = new_time

						if len(self.pairs) >= 20:
							url = base_url + 'ALL'
							res = urlopen(url, timeout=5)

							if not res:
								continue

							msg = json.loads(res.read().decode())

							for market in self.markets:
								market_book = msg[market.symbol()]
								
								bids = {}
								bid_data = market_book['bids']
								for bid_object in bid_data:
									price = Decimal(bid_object['price']).quantize(market.tick_size())
									size = Decimal(bid_object['quantity']).quantize(market.tick_size())

									bids[price] = size

								asks = {}
								ask_data = market_book['asks']
								for ask_object in ask_data:
									price = Decimal(ask_object['price']).quantize(market.tick_size())
									size = Decimal(ask_object['quantity']).quantize(market.tick_size())

									asks[price] = size

								market.reset_book(bids, asks)
						else:
							for market in self.markets:
								url = base_url + market.symbol()
								#print("Connecting to", url)
								msg = json.loads(urlopen(url, timeout=5).read().decode())

								bids = {}
								bid_data = msg['data']['bids']
								for bid_object in bid_data:
									price = Decimal(bid_object['price']).quantize(market.tick_size())
									size = Decimal(bid_object['quantity']).quantize(market.tick_size())

									bids[price] = size

								asks = {}
								ask_data = msg['data']['asks']
								for ask_object in ask_data:
									price = Decimal(ask_object['price']).quantize(market.tick_size())
									size = Decimal(ask_object['quantity']).quantize(market.tick_size())

									asks[price] = size

								market.reset_book(bids, asks)
				except socket.timeout:
					pass
				except URLError:
					print("Bithumb: Connection error")
				except Exception:
					traceback.print_exc()

				# Bithumb API only updates every 30 seconds 
				sleep(10)

		self.running = True
		self._thread = Thread(target=_loop)
		self._thread.start()

	def stop(self):
		self.running = False
		self._thread.join()
		self.markets.clear()

if __name__ == '__main__':
	def main():
		pairs = [(BTC, KRW), (LTC, KRW), (ETH, KRW)]
		cli = Level2BithumbClient(pairs)
		cli.start()
		for i in range(100):
			for market in cli.markets:
				print(market.disp_name(), market.best_bid())
			print("-----------------------")
			sleep(2)
		cli.stop()

	main()