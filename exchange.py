__all__ = ['Exchange']

""" Represents a cryptocurrency exchange """
class Exchange(object):
	""" Returns the name of the Exchange as a string """
	def name(self):
		raise NotImplementedError("Method 'name' from class 'Exchange' not implemented")

	"""
		Returns a fixed fee to move the asset to another wallet/exchange.
		The number should be represented with the Decimal class
	"""
	def withdrawal_fee(self, asset):
		raise NotImplementedError("Method 'withdrawl_fee' from class 'Exchange' not implemented")

	def __str__(self):
		return self.name()