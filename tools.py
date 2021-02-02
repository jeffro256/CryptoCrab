def first(iterable, condition = lambda x: True):
	return next((x for x in iterable if condition(x)), None)
