from decimal import Decimal
import json
import os.path
from urllib.request import urlopen
from time import time

__all__ = ['get_rate']

_fixer_url = 'http{}://data.fixer.io/api/latest?access_key={}'
_save_file_name = os.path.join(os.path.dirname(__file__), 'fixer_save.json')

# Relatively expensive call, try to cache results if possible. I only save 
# results in file because the free fixer subscription only allows 1000 calls/mo.
def get_rate(targ_curr, base_curr, key, min_wait=7500, secure=False):
	save_file = open(_save_file_name, 'r+')
	saved_data = json.loads(save_file.read())

	now = time()

	if not saved_data or now > saved_data['timestamp'] + min_wait:
		url = _fixer_url.format('s' if secure else '', key)
		fixer_response = json.loads(urlopen(url).read())

		if fixer_response['success']:
			fixer_data = fixer_response

			save_file.seek(0)
			save_file.truncate(0)
			save_file.write(json.dumps(fixer_data))
		else:
			raise EnvironmentError("API endpoint: {} gave error: {}", url, fixer_response['error'])
	else:
		fixer_data = saved_data

	save_file.close()

	# NOTE: Rates are flipped, everything is priced in EUR, but the rate number
	# returned for a currency C is given as EUR/C not C/EUR
	rate1 = fixer_data['rates'][targ_curr]
	rate2 = fixer_data['rates'][base_curr]

	# Do actual significant figure division later
	quantizer = Decimal('0.' + ('0' * (max(len(str(rate1)), len(str(rate2))) - 1)) + '1')
	
	return Decimal(rate2 / rate1).quantize(quantizer)
