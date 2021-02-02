""" A singleton class to be used as a decorator """
class Singleton(object):
	def __init__(self, decorated):
		self._decorated = decorated
		self._instance = None

	def instance(self):
		if self._instance is None:
			self._instance = self._decorated()

		return self._instance

	def __call__(self):
		raise TypeError("Singleton constructors cannot be accessed directly." +
						" Call '.instance()' instead")

	def __instancecheck__(self, inst):
		return isinstance(inst, self._decorated)