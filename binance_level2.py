from decimal import Decimal
import exchanges
import json
import market
import ssl
from threading import Thread
from tickers import *
import time
from tools import first
import traceback
from urllib.request import urlopen
from websocket import WebSocketApp

__all__ = ['Level2BinanceClient']

class Level2BinanceClient(object):
	def __init__(self, pairs):
		if len(pairs) == 0:
			raise ValueError("The argument passed, 'pairs', is empty!")

		self.pairs = pairs
		self.markets = []
		self._should_run = False
		self._wsapp = None
		self._thread = None
		self._event_buffer = []
		self._last_update = {}

		# Binance for some reason has Bitcoin Cash's ticker as BCC
		self._convert_sym = lambda s: ('BCC' if s == BCH else ('IOTA' if s == IOTA else s))
		self._symbols = [''.join(map(self._convert_sym, p)) for p in pairs]
		self._got_book = { s: False for s in self._symbols }

	def _on_open(self, ws):
		tick_sizes = {}
		step_sizes = {}

		exchange_info_url = 'https://api.binance.com/api/v1/exchangeInfo'
		exchange_info = json.loads(urlopen(exchange_info_url).read().decode())

		for symbol_info in exchange_info['symbols']:
			symbol = symbol_info['symbol']

			if symbol not in self._symbols:
				continue

			filters = symbol_info['filters']
			ftype = 'filterType'
			tick_size = first(filters, lambda f: f[ftype] == 'PRICE_FILTER')['tickSize']
			step_size = first(filters, lambda f: f[ftype] == 'LOT_SIZE')['stepSize']

			tick_sizes[symbol] = Decimal(tick_size.rstrip('0'))
			step_sizes[symbol] = Decimal(step_size.rstrip('0'))

		for i in range(len(self.pairs)):
			pair = self.pairs[i]
			name = '{}/{}'.format(*map(self._convert_sym, pair))
			symbol = self._symbols[i]
			exchange = exchanges.BinanceExchange.instance()
			ts = tick_sizes[symbol]
			ss = step_sizes[symbol]
			market_ = market.BasicMarket(name, pair, symbol, exchange, ts, ss)
			self.markets.append(market_)

	def _on_message(self, ws, msg_str):
		msg = json.loads(msg_str)

		self._event_buffer.append(msg)

		self._process_events()

	def _on_error(self, ws, error):
		print("Binance Websocket Error:", error)
		print("Traceback (most recent call last):")
		traceback.print_tb(error.__traceback__)

		print("Restarting...")

		ws.close()

	def _on_close(self, ws):
		print("Closing Binance Websocket...")

		self.markets.clear()
		self._event_buffer.clear()
		self._last_update.clear()
		self._got_book = { s: False for s in self._symbols }

	def start(self):
		if self._should_run:
			return

		self._should_run = True

		stream_names = [s.lower() + '@depth' for s in self._symbols]
		stream_base = 'wss://stream.binance.com:9443'
		stream_endpoint = ('/ws/' if len(self.pairs) == 1 else '/stream?streams=') + '/'.join(stream_names)
		stream_url = stream_base + stream_endpoint

		def _run():
			while self._should_run:
				self._wsapp = WebSocketApp(stream_url,
					on_open=self._on_open,
					on_message=self._on_message,
					on_error=self._on_error,
					on_close=self._on_close
				)

				self._wsapp.run_forever(sslopt={'cert_reqs': ssl.CERT_NONE})

		self._thread = Thread(target=_run)
		self._thread.start()

	def stop(self):
		if not self.is_running():
			return

		self._should_run = False
		self._wsapp.close()
		self._thread.join()

	def is_running(self):
		return self._thread.isAlive() if self._thread else False

	def _process_events(self):
		i = 0
		while i < len(self._event_buffer):
			msg = self._event_buffer[i] if len(self.markets) == 1 else self._event_buffer[i]['data']
			symbol = msg['s']

			market = first(self.markets, lambda m: m.symbol() == symbol)

			first_update = msg['U']
			end_update = msg['u']

			if not self._got_book[symbol]:
				self._reset_book(market)

			if symbol not in self._last_update:
				i += 1
			elif end_update <= self._last_update[symbol]:
				del self._event_buffer[i]
			elif first_update > self._last_update[symbol] + 1:
				print("Skipped on {}: {}!".format('Binance', market.disp_name()))
				print(self._last_update[symbol])
				exit()
			else:
				bids = msg['b']
				asks = msg['a']

				tick_size = market.tick_size()
				step_size = market.step_size()

				for bid in bids:
					price = Decimal(bid[0]).quantize(tick_size)
					size = Decimal(bid[1]).quantize(step_size)

					market.update_bid(price, size)

				for ask in asks:
					price = Decimal(ask[0]).quantize(tick_size)
					size = Decimal(ask[1]).quantize(step_size)

					market.update_ask(price, size)

				del self._event_buffer[i]
				self._last_update[symbol] = end_update

	def _reset_book(self, market, limit=500):
		symbol = market.symbol()
		rest_url = 'https://www.binance.com/api/v1/depth?symbol={}&limit={}'.format(symbol, limit)

		data_str = urlopen(rest_url).read().decode()
		data = json.loads(data_str)

		print("Got Binance", market.symbol(), "snapshot:", len(data_str), "bytes")

		raw_bids = data['bids']
		raw_asks = data['asks']
		last_update = data['lastUpdateId']

		bids = {}
		asks = {}

		for bid in raw_bids:
			price = Decimal(bid[0]).quantize(market.tick_size())
			size = Decimal(bid[1]).quantize(market.step_size())

			bids[price] = size

		for ask in raw_asks:
			price = Decimal(ask[0]).quantize(market.tick_size())
			size = Decimal(ask[1]).quantize(market.step_size())

			asks[price] = size

		market.reset_book(bids, asks)

		self._last_update[symbol] = last_update
		self._got_book[symbol] = True

if __name__ == '__main__':
	def main():
		cli = Level2BinanceClient([(LTC, BTC), (ETH, BTC), (XRP, BTC), (BCH, BTC), (IOTA, BTC)])
		cli.start()
		markets = cli.markets
		for t in range(30):
			time.sleep(2)
			for market in markets:
				print(market.disp_name(), '--', market.best_bid(), market.best_ask())
			print("-----------------------")
		cli.stop()
		print("Goodbye!")

	main()