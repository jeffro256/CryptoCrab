from decimal import Decimal
from exchange import Exchange
import json
import os
from singleton import Singleton
from urllib.request import urlopen

__all__ = ['GDAXExchange', 'BinanceExchange', 'BithumbExchange']

@Singleton
class GDAXExchange(Exchange):
	def name(self):
		return 'GDAX'

	def withdrawl_fee(self, asset):
		return Decimal('0')

@Singleton
class BinanceExchange(Exchange):
	def __init__(self):
		self._withdrawal_fees = {}
		self.reload()

	def name(self):
		return 'Binance'

	def withdrawal_fee(self, asset):
		return self._withdrawl_fees[asset]

	def reload(self):
		withdrawal_fee_url = 'https://www.binance.com/assetWithdraw/getAllAsset.html'
		resp = urlopen(withdrawal_fee_url)
		data = json.loads(resp.read().decode())

		# The binance URL supplies the transaction fees as real floats, 
		# which sometimes causes rounding errors
		arb_quantizer = Decimal('0.0001')
		self._withdrawl_fees = { x['assetCode']: \
			Decimal(x['transactionFee']).quantize(arb_quantizer) for x in data }

		self._withdrawl_fees['MIOTA'] = self._withdrawl_fees['IOTA']
		del self._withdrawl_fees['IOTA']

@Singleton
class BithumbExchange(Exchange):
	def __init__(self):
		self._withdrawl_fees = {}

		self.reload()

	def name(self):
		return 'Bithumb'

	def withdrawal_fee(self, asset):
		return self._withdrawl_fees[asset]

	def reload(self):
		"""
			Bithumb doesn't have an easy way of finding the withdrawal fees
			without a webpage scraper
		"""
		wd_fee_path = os.path.join(os.path.dirname(__file__), 'bithumb_wd_fees.txt')

		self._withdrawl_fees.clear()

		with open(wd_fee_path) as f:
			for line in f:
				asset, fee = line.split()
				fee = Decimal(fee)

				self._withdrawl_fees[asset] = fee

@Singleton
class BitstampExchange(Exchange):
	def name(self):
		return 'Bitstamp'

	def withdrawl_fee(self, asset):
		return Decimal('0')

