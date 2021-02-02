import logging
import pysher

class Connection(pysher.Connection):
	def bind_time_out(self, callback):
		if not hasattr(self, 'time_out_callbacks'):
			self.time_out_callbacks = []

		self.time_out_callbacks.append(callback)

	def _connection_timed_out(self):
		print("timeout called")
		if hasattr(self, 'time_out_callbacks'):
			for callback in time_out_callbacks:
				callback()

		super()._connection_timed_out()

class Pusher(pysher.Pusher):
	def __init__(self, key, secure=True, secret=None, user_data=None, 
				 log_level=logging.INFO, daemon=True, port=None,
				 reconnect_interval=10, custom_host=None, auto_sub=False,
				 http_proxy_host=None, http_proxy_port=None, http_no_proxy=None,
				 http_proxy_auth=None, **thread_kwargs):
		self.key = key
		self.secret = secret
		self.user_data = user_data or {}

		self.channels = {}
		self.url = self._build_url(key, secure, port, custom_host)

		if auto_sub:
			reconnect_handler = self._reconnect_handler
		else:
			reconnect_handler = None

		self.connection = Connection(self._connection_handler, self.url,
									 reconnect_handler=reconnect_handler,
									 log_level=log_level,
									 daemon=daemon,
									 reconnect_interval=reconnect_interval,
									 socket_kwargs=dict(http_proxy_host=http_proxy_host,
														http_proxy_port=http_proxy_port,
														http_no_proxy=http_no_proxy,
														http_proxy_auth=http_proxy_auth),
									 **thread_kwargs)