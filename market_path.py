from decimal import Decimal
import traceback

__all__ = ['ArbitragePath', 'compile_market_paths', 'run_path']

class ArbitragePath(object):
	STATUS_OK = 'OK'
	STATUS_INCOMPLETE = 'INCOMPLETE'

	BUY = 'BUY'
	SELL = 'SELL'

	# Assumes path variable isn't discontinuous
	def __init__(self, baseasset, path=[], leftovers=None):
		self.base_asset = baseasset
		self.path = path

		if leftovers is None:
			self._leftovers = []

			for market in path:
				pair = market.pair()

				curr_asset = baseasset if len(self._leftovers) == 0 else self._leftovers[-1]

				if curr_asset == pair[0]:
					self._leftovers.append(pair[1])
				elif curr_asset == pair[1]:
					self._leftovers.append(pair[0])
				else:
					raise ValueError("Discontinuous path passed to ArbitragePath constructor")
					break
		else:
			self._leftovers = leftovers

	def get(self, index):
		return self.path[index]

	def side(self, index):
		curr_asset = self._leftovers[index]
		pair = self.path[index].pair()
		
		if curr_asset == pair[0]:
			return self.BUY
		else:
			return self.SELL

	def add(self, market):
		if self.current_asset() not in market.pair():
			error_msg = "Adding market {}: {} would make path discontinous" \
			            .format(market.exchange(), market.disp_name())
			raise ValueError(error_msg)

		self.path.append(market)

		pair = market.pair()
		leftover = pair[1] if self.current_asset() == pair[0] else pair[0]
		self._leftovers.append(leftover)

	def status(self):
		curr_currency = self.current_asset()

		if curr_currency == self.base_asset and len(self) > 0:
			return self.STATUS_OK
		else:
			return self.STATUS_INCOMPLETE

	def current_asset(self):
		return self._leftovers[-1] if len(self._leftovers) != 0 else self.base_asset

	def copy(self):
		return ArbitragePath(self.base_asset, self.path[:], self._leftovers[:])

	def __len__(self):
		return len(self.path)

	def __contains__(self, value):
		return value in self.path

	def __str__(self):
		res = '{:>5}: '.format(self.base_asset)
		for i in range(len(self)):
			m = self.get(i)
			e_name = m.exchange().name().upper()
			e_name = e_name[(3 if e_name.startswith('BIT') else 0):][:4]

			res += '({:4} {:>4} -- {:>8})'.format(
			self.side(i).capitalize(), 
			e_name, 
			self.get(i).disp_name())

			if i != len(self) - 1:
				res += ' -> '

		return res

def compile_market_paths(markets, max_length):
	markets_by_ticker = {}

	for market in markets:
		pair = market.pair()

		for ticker in pair:
			if ticker in markets_by_ticker:
				markets_by_ticker[ticker].append(market)
			else:
				markets_by_ticker[ticker] = [market]

	old_batch = []
	market_paths = []

	for ticker in markets_by_ticker:
		for market in markets_by_ticker[ticker]:
			old_batch.append(ArbitragePath(ticker, path=[market]))

	for i in range(1, max_length):
		new_batch = []

		for path in old_batch:
			next_ticker = path.current_asset()
			for next_market in markets_by_ticker[next_ticker]:

				if next_market in path:
					continue

				new_path = path.copy()
				new_path.add(next_market)
				new_batch.append(new_path)

		old_batch = [path for path in new_batch if path.status() == ArbitragePath.STATUS_INCOMPLETE]
		market_paths += [path for path in new_batch if path.status() == ArbitragePath.STATUS_OK]

	return market_paths

# Use the tick and step size to round amounts
def run_path(path, base_asset_amount):
	if path.status() != ArbitragePath.STATUS_OK:
		raise ValueError("{{{}}} is not a valid full path".format(path))

	old_amount = base_asset_amount
	too_shallow = False

	avg_prices = []

	for i in range(len(path)):
		market = path.get(i)
		new_amount = Decimal('0')

		if path.side(i) == ArbitragePath.BUY:
			asks = market.asks()

			for ask in asks:
				if old_amount <= 0:
					break

				price = ask[0]
				size = min(ask[1] * price, old_amount)

				old_amount -= size
				new_amount += size / price

			if old_amount > 0:
				too_shallow = True
		else:
			bids = market.bids()

			for bid in bids:
				if old_amount <= 0:
					break

				price = bid[0]
				size = min(bid[1], old_amount)

				old_amount -= size
				new_amount += size * price

			if old_amount > 0:
				too_shallow = True

		old_amount = new_amount

	return (new_amount, too_shallow, avg_prices)

if __name__ == '__main__':
	import dummy_factory
	a = compile_market_paths(dummy_factory.test_dummies, 4)
	for x in a:
		print(x)

