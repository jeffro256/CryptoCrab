import datetime

__all__ = ['touch', 'feel', 'ttouch']

_obj = {}

def touch(name, val):
	res = _obj[name]
	if val is None:
		del _obj[name]
	else:
		_obj[name] = val
	return res

def feel(name):
	return _obj[name]

def ttouch(name):
	_obj[name] = datetime.datetime.now()