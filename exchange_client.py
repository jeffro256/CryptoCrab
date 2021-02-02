class ExchangeClient(object):
	def __init__(self):
		raise NotImplementedError("Cannot initialize interface 'ExchangeClient'")

	def get_pairs(self):
		raise NotImplementedError("'get_pairs' in 'ExchangeClient' subclass not implemented")

	def set_pairs(self, pairs):
		raise NotImplementedError("'set_pairs' in 'ExchangeClient' subclass not implemented")

	def start(self):
		raise NotImplementedError("'start' in 'ExchangeClient' subclass not implemented")

	def stop(self):
		raise NotImplementedError("'stop' in 'ExchangeClient' subclass not implemented")

	def get_markets(self):
		raise NotImplementedError("'get_markets' in 'ExchangeClient' subclass not implemented")