from decimal import Decimal
import exchanges
import gdax
import json
import market
from tickers import *
import time
from tools import first

__all__ = ['Level2GDAXClient']

class Level2GDAXClient(gdax.WebsocketClient):
	def __init__(self, pairs=[(BTC, USD)]):
		products = ['{}-{}'.format(*p) for p in pairs]
		super().__init__(products=products)

		self._pairs = pairs
		self._cli = gdax.PublicClient()

	def on_open(self):
		self.markets = []
		
		disp_names = ['{}/{}'.format(*p) for p in self._pairs]
		product_info = self._cli.get_products()
		for i in range(len(self._pairs)):
			exchange = exchanges.GDAXExchange.instance()
			try:
				pinfo = first(product_info, lambda x: x['id'] == self.products[i])
			except:
				print(product_info)
				exit()
			tick_size = Decimal(pinfo['quote_increment'])
			market_ = market.BasicMarket(disp_names[i], self._pairs[i], 
					  self.products[i], exchange, tick_size, Decimal('0.00000001'))
			self.markets.append(market_)

		self.channels = [
			{
				'name': 'level2',
				'product_ids': self.products
			},
			{
				'name': 'matches',
				'product_ids': self.products
			}
		]

	def on_message(self, msg):
		msg_type = msg['type']

		if msg_type == 'subscriptions':
			return

		if 'product_id' not in msg:
			print("Bad MSG:", msg)
		product = msg['product_id']

		market = first(self.markets, lambda m: m.symbol() == product)

		if msg_type == 'snapshot':
			print("Got GDAX", product, "snapshot:", len(json.dumps(msg)), "bytes")
			qinc = market.tick_size()
			ssize = market.step_size()
			bids = { Decimal(p).quantize(qinc): Decimal(s).quantize(ssize) for (p, s) in msg['bids'] }
			asks = { Decimal(p).quantize(qinc): Decimal(s).quantize(ssize) for (p, s) in msg['asks'] }
			market.reset_book(bids, asks)
		elif msg_type == 'last_match' or msg_type == 'match':
			qinc = market.tick_size()
			price = Decimal(msg['price']).quantize(qinc)
			market.match(price)
		elif msg_type == 'l2update':
			changes = msg['changes']
			qinc = market.tick_size()
			ssize = market.step_size()

			for change in changes:
				side = change[0]
				price = Decimal(change[1]).quantize(qinc)
				size = Decimal(change[2]).quantize(ssize)

				if side == 'buy':
					market.update_bid(price, size)
				else:
					market.update_ask(price, size)

	def on_close(self):
		print("Closing GDAX Websocket Client...")

if __name__ == '__main__':
	wsClient = Level2GDAXClient([(BTC, USD), (LTC, USD), (ETH, USD)])
	wsClient.start()
	for i in range(120):
		for market in wsClient.markets:
			print(market.disp_name(), str(market.best_bid()).rjust(8), str(market.best_ask()).rjust(8), sep='\t')
		print("-------------------------")
		time.sleep(1)
	wsClient.close()