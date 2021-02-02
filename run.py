import datetime
from decimal import Decimal
import fixer
import json
import market
import market_path
import sys
from tickers import *
import time
from tools import first
from urllib.request import urlopen
from wap import wap

from gdax_level2 import Level2GDAXClient
from binance_level2 import Level2BinanceClient
from bithumb_level2 import Level2BithumbClient
from bitstamp_client import BitstampClient

if '-h' in sys.argv or '-help' in sys.argv:
	print("Usage: run.py [-c config_path] [-v] [-h | -help]")
	print("""        -c config_path: Supply an alternate config path. Defaults
		                             to './config.json'
		             -v            : Enable verbose mode
		             -h | -help    : Show usage guide
		  """)
	exit()

verbose = '-v' in sys.argv

kimchi_bid_target = kimchi_ask_target = None

for i, arg in enumerate(sys.argv):
	if arg == '-s':
		kimchi_bid_target = int(sys.argv[i + 1])
		kimchi_ask_target = int(sys.argv[i + 2])
		break

config_path = 'config.json'
if '-c' in sys.argv:
	config_path = sys.argv[sys.argv.index('-c')+1]

with open(config_path) as cfg_file:
	cfg_contents = cfg_file.read()

cfg_data = json.loads(cfg_contents)
parse_pairs = lambda a: [tuple(x.split('/')) for x in a]
gdax_pairs = parse_pairs(cfg_data['pairs']['GDAX'])
binance_pairs = parse_pairs(cfg_data['pairs']['Binance'])
bithumb_pairs = parse_pairs(cfg_data['pairs']['Bithumb'])
bitstamp_pairs = parse_pairs(cfg_data['pairs']['Bitstamp'])
usd_depth = Decimal(cfg_data['usd_depth'])
kimchi_depth = Decimal(cfg_data['kimchi_depth']) 
fixer_key = cfg_data['fixer_key']

coinmarketcap_url = 'https://api.coinmarketcap.com/v1/ticker/'
resp = urlopen(coinmarketcap_url)
data = json.loads(resp.read().decode())

asset_prices = { t['symbol']: Decimal(t['price_usd']) for t in data if int(t['rank']) <= 100 }

asset_amounts = { k: usd_depth / asset_prices[k] for k in asset_prices }
asset_amounts['USD'] = usd_depth
asset_amounts['EUR'] = usd_depth * fixer.get_rate('USD', 'EUR', fixer_key)

gdax_cli = Level2GDAXClient(gdax_pairs)
binance_cli = Level2BinanceClient(binance_pairs)
bithumb_cli = Level2BithumbClient(bithumb_pairs)
bitstamp_cli = BitstampClient()
bitstamp_cli.set_pairs(bitstamp_pairs)
gdax_cli.start()
binance_cli.start()
bithumb_cli.start()
bitstamp_cli.start()

# Hack until I can get markets before REST API loads
while (not gdax_cli.markets) or (not binance_cli.markets) or (not bithumb_cli.markets):
	time.sleep(1)

markets = []
markets += gdax_cli.markets
markets += binance_cli.markets
markets += bithumb_cli.markets
markets += bitstamp_cli.get_markets()

old_t = time.perf_counter()
arb_paths = market_path.compile_market_paths(markets, 3)
new_t = time.perf_counter()
elapsed_str = Decimal(new_t - old_t).quantize(Decimal('0.001'))
print("Arbitrages found: {}.".format(len(arb_paths)), "Time: {}s".format(elapsed_str))

arb_paths = [path for path in arb_paths if path.base_asset != KRW]

if verbose:
	print("#################################################")
	print("ARBITRAGE PATHS:")
	for path in arb_paths:
		print(path)
	print("#################################################")

time.sleep(15)

gdax_btc_market = first(gdax_cli.markets, lambda m: m.pair() == (BTC, USD))
bithumb_btc_market = first(bithumb_cli.markets, lambda m: m.pair() == (BTC, KRW))
krw_usd_rate = fixer.get_rate('KRW', 'USD', fixer_key)
print("Using USD/KRW rate:", str(1 / krw_usd_rate)[:7])

def get_best_path(paths, asset_amounts):
	best_roi = Decimal('0')
	best_path = None

	for path in arb_paths:
		start_amount = asset_amounts[path.base_asset]
		path_res = market_path.run_path(path, start_amount)

		if path_res[1]:
			continue

		end_amount = path_res[0]
		roi = (end_amount - start_amount) / start_amount

		# START HACK (plz do this correctly sometime)
		e_fees = {
			'GDAX': Decimal('0.0025'),
			'Binance': Decimal('0.001'),
			'Bithumb': Decimal('0.0015'),
			'Bitstamp': Decimal('0.0025')
		}

		for i in range(len(path)):
			m = path.get(i)
			e_n = m.exchange().name()

			roi -= e_fees[e_n]
		# END HACK

		if best_path is None or roi > best_roi:
			best_roi = roi
			best_path = path

	return (best_path, best_roi)

while True:
	try:
		best_path, best_roi = get_best_path(arb_paths, asset_amounts)

		now = datetime.datetime.now()
		now_str = now.strftime("[%a %H:%M:%S]")
		us_btc = gdax_btc_market.best_ask()
		kor_btc = bithumb_btc_market.best_bid()
		if not us_btc or not kor_btc:
			kimchi_str = "KS = ___ USD (____%)."
		else:
			gdax_bid_wap = wap(gdax_btc_market, kimchi_depth, market.BID, market.QUOTE_CURR)
			gdax_ask_wap = wap(gdax_btc_market, kimchi_depth, market.ASK, market.QUOTE_CURR)
			bithumb_bid_wap = wap(bithumb_btc_market, kimchi_depth / krw_usd_rate, market.BID, market.QUOTE_CURR)
			bithumb_ask_wap = wap(bithumb_btc_market, kimchi_depth / krw_usd_rate, market.ASK, market.QUOTE_CURR)
			kimchi_spread1 = bithumb_bid_wap * krw_usd_rate - gdax_ask_wap
			kimchi_spread2 = bithumb_ask_wap * krw_usd_rate - gdax_bid_wap 
			ks1_quantized = kimchi_spread1.quantize(Decimal('1'))
			ks2_quantized = kimchi_spread2.quantize(Decimal('1'))
			kimchi_str = "KS = {} USD / {} USD.".format(ks1_quantized, ks2_quantized)
			
			if kimchi_bid_target is not None and kimchi_ask_target is not None:
				if kimchi_spread1 <= kimchi_bid_target:
					kimchi_str += ' *** BUY ***.'
				elif kimchi_spread2 >= kimchi_ask_target:
					kimchi_str += ' *** SELL ***.' 
		if best_roi < Decimal('0.001'):
			best_path = "..."
			roi_str = "Net ROI = None. "
		else:
			roi_perc = (best_roi * Decimal('100')).quantize(Decimal('0.01'))
			roi_str = "Net ROI = {}%.".format(roi_perc)

		if us_btc is None:
			btc_str = "[GDAX BTC] = $____"
		else:
			btc_str = "[GDAX BTC] = ${}".format(us_btc.quantize(Decimal('1')))
		
		time_format = '%I:%M %p'
		now = datetime.datetime.now()
		gdax_time = gdax_cli.markets[0].last_updated()
		binance_time = binance_cli.markets[0].last_updated()
		bithumb_time = bithumb_cli.markets[0].last_updated()
		bitstamp_time = bitstamp_cli.get_markets()[0].last_updated()

		datetime_to_timestr = lambda x: x.strftime(time_format) if x else None
		time_strs = map(datetime_to_timestr, [now, gdax_time, binance_time, bithumb_time, bitstamp_time])

		lpadding = " "*len(now_str)

		print(now_str, best_path)
		print(lpadding + roi_str, kimchi_str, btc_str, sep="   ")
		if verbose:
			print(lpadding + "Times: Now[{}] GDAX[{}] Binance[{}] Bithumb[{}] Bitstamp[{}]".format(*time_strs))

		time.sleep(10)
	except KeyboardInterrupt:
		break

gdax_cli.close()
binance_cli.stop()
bithumb_cli.stop()
bitstamp_cli.stop()

print("Goodbye!")
