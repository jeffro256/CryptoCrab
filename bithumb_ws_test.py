from decimal import Decimal
import exchanges
import json
import market
import traceback
import websocket

url = 'wss://wss.bithumb.com/public'

if __name__ == '__main__':
	market_ = market.BasicMarket('ETH/KRW', ('ETH', 'KRW'), 'ETH', 'Bithumb', Decimal('100'), Decimal('0.00000001'))

	i = 0
	currencies = ['BTC', 'ETH', 'LTC', 'XMR', 'DASH']

	def o(ws):
		pass

	def m(ws, msg_str):
		msg = json.loads(msg_str)
		if msg['header']['service'] == 'orderbook':
			print(msg['header']['currency'])
			print(msg['data'], end='\n\n')

		global i
		send_data = json.dumps({
			'currency': currencies[i % len(currencies)],
			'service': 'orderbook'
		})

		ws.send(send_data)

		i += 1

	def c(ws):
		print("Closing")

	def e(ws, error):
		print(error)
		traceback.print_tb(error.__traceback__)

	header = ['Origin: https://www.bithumb.com']
	#websocket.enableTrace(True)
	wsapp = websocket.WebSocketApp(
		url,
		on_open=o,
		on_message=m,
		on_close=c,
		on_error=e,
		header=header
	)

	try:
		wsapp.run_forever()
	except KeyboardInterrupt:
		pass
	print("Done")

class Level2BithumbClient(object):
	def __init__(self, pairs):
		self.pairs = pairs
		self.markets = []
		self._wss = []

	def start(self):
		if self.is_running():
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

		step_size = Decimal('0.00000001')

		for pair in self.pairs:
			name = '{}/{}'.format(*pair)
			symbol = pair[0]
			exchange = exchanges.BithumbExchange.instance()
			tick_size = tick_sizes[symbol]
			market_ = market.BasicMarket(name, pair, symbol, exchange, tick_size, step_size)

			self.markets.append(market_)

			ws_url = 'wss://wss.bithumb.com/public'
			header = 'Origin: https://bithumb.com'
			ws = websocket.create_connection(ws_url, header=header)

			data = { 'currency': symbol, 'service': 'orderbook' } 

			msg = json.dumps(data).encode()

			ws.send(msg)

		header = ['Origin: https://www.bithumb.com']

		for pair in self.pairs:
			name = '{}/{}'.format()

	def stop(self):
		if not self.is_running():
			return

		print("Stopping Level2BithumbClient...")
		for ws in self._wss:
			ws.close()

	def is_running(self):
		pass

	def _create_onopen(self, markets):
		def _onopen(ws):
			pass

		return _onopen

	def _create_onmessage(self, markets):
		msg_num = 0
		
		def _onmessage(ws, msg):
			pass

		return _onmessage

	def _create_onerror(self, markets):
		def _onerror(ws, error):
			print(error)
			traceback.print_tb(error.__traceback__)
			ws.close()

		return _onerror

	def _create_onclose(self, markets):
		def _onclose(ws):
			pass

		return _onclose
