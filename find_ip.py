#!/usr/bin/env python3
# -*- coding: utf-8 -*-



#########################
# Dependencies
#########################
# karellen-sqlite
# tornado



#########################
# Modules
#########################

import ipaddress
import json
import __main__ as main
from multiprocessing import Pool, cpu_count
from os import path, getpid
import sqlite3
from karellen.sqlite3 import Connection
import random
import subprocess
import sys
import time
from tornado import concurrent, ioloop, web, websocket
import urllib.request



#########################
# Global Variables
#########################

script_name = path.basename(main.__file__)
script_purpose = 'Display IP addresses on map.'

# Returns the path of the current script.
script_path = path.dirname(path.realpath(__file__))

db = {
	# Path to database file.
	'path': './database.db',
	# Database connection. Don't edit.
	'conn': None
}

server = {
	'ip': '127.0.0.1',
	'port': 8080,
	# The IOloop. Don't edit.
	'ioloop': None
}

# Clients connected via WebSocket.
clients = set()

# First IP as an integer.
first_ip_int = 0

# Last IP as an integer.
last_ip_int = 4294967296



#########################
# Functions
#########################

def print_message(message, exit=False):
	"""Print a message to stdout. Optionally exit."""
	if exit:
		sys.exit(message)
	print(message)

def db_hook(conn, op, db_name, table_name, rowid):
	"""Called after database is changed.

	Don't modify conn!

	Keyword arguments:
	conn       -- database connection.
	op         -- type of database operation executed.
	db_name    -- name of database operated on.
	table_name -- name of table operated on.
	rowid      -- id of affected row.
	"""

	try:
		for row in db['conn'].execute('SELECT * FROM hosts WHERE rowid=?', (str(rowid),)):
			row_json = json.dumps(dict(row))
			ws_send_message(row_json)
	except Exception as error:
		print_message('db_hook error = {0}'.format(error), False)

def db_connect(db_path):
	"""Connect to database."""
	if not path.isfile(db_path):
		# Create database. conn.commit() is called automatically.
		with sqlite3.connect(db_path, factory=Connection) as conn:
			conn.execute('''CREATE TABLE hosts (
							host TEXT PRIMARY KEY,status TEXT,time_pinged TEXT,
							country TEXT,countryCode TEXT,region TEXT,
							regionName TEXT,city TEXT,zip TEXT,
							lat REAL,lon REAL,timezone TEXT,isp TEXT,
							asys TEXT,mobile TEXT,org TEXT,proxy TEXT,
							reverse TEXT);''')
		conn.close()
	with sqlite3.connect(db_path, factory=Connection, check_same_thread=False) as conn:
		# Database exists. Set hook.
		# check_same_thread=False allows conn to be shared amoung threads.
		conn.set_update_hook(db_hook)
		# Query results returned as a dictionary.
		conn.row_factory = sqlite3.Row
		return conn

def ws_send_message(message):
	"""Send message to all clients. Remove dead clients."""
	removable = set()
	for c in clients:
		if not c.ws_connection or not c.ws_connection.stream.socket:
			removable.add(c)
		else:
			c.write_message(message)
			#print_message('ws_send_message called!', False)
	for c in removable:
		clients.remove(c)
		print_message('Removed dead client.', False)

def ip_to_loc(host):
	"""Get location info about IP address."""
	# 262143 means get all available fields.
	url = 'http://ip-api.com/json/{0}?fields=262143'.format(host)
	with urllib.request.urlopen(url) as f:
		# Returns a JSON string.
		response = f.read().decode('utf-8')
		# Convert to Python dictionary.
		return json.loads(response)

def ping(host):
	"""Ping each host using a separate process/core."""
	#print_message('host = {0}'.format(host), False)
	#print_message('Child process ID = {0}'.format(getpid()), False)

	# Stop after sending this many ECHO_REQUEST packets.
	tries = '3'
	# The final ping command.
	cmd = ['ping', '-c', tries, host]
	# Execute cmd, wait for it to complete, then return a CompletedProcess instance.
	# Capture stdout and stderr.
	result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	# Get location info about IP address.
	ip_loc_dict = ip_to_loc(host)

	host_info = {
		'ping_output': result,
		'location': ip_loc_dict
	}
	return host_info

def parse_ping(host_info=None):
	"""A coroutine. Parse ping result, update database.

	Keyword arguments:
	host_info -- a dictionary, returned from ping().
	"""

	while True:
		# (yield) turns this function into a coroutine.
		# The function argument value (host_info) is accessed by yield.
		result = (yield)
		#print_message('result = {0}'.format(result), False)
		# The pinged host.
		host = result['ping_output'].args[3]
		# 0 = host online. 1 = host offline.
		return_code = result['ping_output'].returncode
		# UTC: time standard commonly used across the world.
		# Returns the time, in seconds, since the epoch as a floating point number.
		utc_time = time.time()

		country = countryCode = region = regionName = \
		city = zip = lat = lon = timezone = isp = \
		asys = mobile = org = proxy = reverse = ''

		# If IP-to-location was successful.
		if result['location']['status'] == 'success':
			country = result['location']['country']
			countryCode = result['location']['countryCode']
			region = result['location']['region']
			regionName = result['location']['regionName']
			city = result['location']['city']
			zip = result['location']['zip']
			lat = result['location']['lat']
			lon = result['location']['lon']
			timezone = result['location']['timezone']
			isp = result['location']['isp']
			asys = result['location']['as']
			mobile = str(result['location']['mobile']).capitalize()
			org = result['location']['org']
			proxy = str(result['location']['proxy']).capitalize()
			reverse = result['location']['reverse']

		# Update database. Basically an UPSERT. First try to update the row.
		db['conn'].execute('''UPDATE hosts SET
								status=?,time_pinged=?,country=?,
								countryCode=?,region=?,regionName=?,
								city=?,zip=?,lat=?,lon=?,timezone=?,
								isp=?,asys=?,mobile=?,org=?,proxy=?,
								reverse=?
								WHERE host=?''',
								(return_code,utc_time,country,
								countryCode,region,regionName,
								city,zip,lat,lon,timezone,
								isp,asys,mobile,org,proxy,
								reverse,host))
		# If update unsuccessful (I.E. the row didn't exist) then insert row.
		db['conn'].execute('''INSERT INTO hosts (
								host,status,time_pinged,country,
								countryCode,region,regionName,
								city,zip,lat,lon,timezone,isp,
								asys,mobile,org,proxy,reverse)
								SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
								WHERE (Select Changes()=0)''',
								(host,return_code,utc_time,country,
								countryCode,region,regionName,
								city,zip,lat,lon,timezone,isp,
								asys,mobile,org,proxy,reverse))
		db['conn'].commit()

def get_random_ips(first_ip_int, last_ip_int, num_cpus):
	"""Create N random IPs. N is number of CPUs."""
	ips = []
	for i in range(num_cpus):
		# Return a random integer N such that a <= N <= b.
		ip_int = random.randint(first_ip_int,last_ip_int)
		# Convert IP integer to actual IP.
		ips.extend([ipaddress.ip_address(ip_int).__str__()])
	return ips

def setup_ping():
	"""Setup process pool, send each host to ping(), send result to ping_result()."""
	num_cpus = cpu_count()
	print_message('CPUs found: {0}'.format(num_cpus), False)

	# A process pool. Defaults to number of cores.
	p = Pool()

	# A reference to the coroutine.
	ping_result = parse_ping()

	try:
		# next() starts the coroutine.
		next(ping_result)
		# imap_unordered: results are returned to the parent
		# as soon as the child sends them.
		while True:
			# Get IP addresses to ping.
			ips = get_random_ips(first_ip_int, last_ip_int, num_cpus)
			# Start pinging.
			for i in p.imap_unordered(ping, ips):
				#print_message('i = {0}'.format(i), False)
				# send() supplies values to the coroutine.
				# Send result of ping to coroutine.
				ping_result.send(i)
	except Exception as error:
		print_message('Error during setup_ping(): {0}'.format(error), False)
		p.close()
		p.terminate()
		# Close the coroutine
		ping_result.close()
	else:
		p.close()
		p.join()
		ping_result.close()

def serve_forever():
	"""Start WebSocket server."""
	global server
	app = web.Application(
		# Routes.
		[
			(r'/', IndexHandler),
			(r'/ws', DefaultWebSocket)
		],
		# Directory from which static files will be served.
		static_path=script_path,
		# Enable debug mode settings.
		debug=True,
	)
	app.listen(server['port'])
	print_message('Server listening at {0}:{1}/'.format(server['ip'], server['port']), False)
	# Returns a global IOLoop instance.
	server['ioloop'] = ioloop.IOLoop.instance()
	# Starts the IO loop.
	server['ioloop'].start()



#########################
# Classes
#########################

class IndexHandler(web.RequestHandler):
	"""Handle non-WebSocket connections."""
	def get(self):
		"""Renders the template with the given arguments as the response."""
		self.render('index.html')

class DefaultWebSocket(websocket.WebSocketHandler):
	"""Handle initial WebSocket connection."""
	def open(self):
		"""Invoked when a new WebSocket is opened."""
		print_message('WebSocket opened.', False)
		# Don't delay and/or combine small messages to minimize the number of packets sent.
		self.set_nodelay(True)
		# Add client to list of connected clients.
		clients.add(self)
		# Send greeting to client.
		#self.write_message('Hello from server! WebSocket opened.')

	def on_message(self, message):
		"""Handle incoming WebSocket messages."""
		print_message('Message incoming: {0}'.format(message), False)
		self.write_message(message)

	def on_close(self):
		"""Invoked when the WebSocket is closed."""
		print_message('WebSocket closed.', False)



#########################
# Start script
#########################

def main():

	print_message('\n***\n* {0}\n* {1}\n***\n'.format(script_name,script_purpose), False)

	# Connect to database.
	global db
	db['conn'] = db_connect(db['path'])
	#print_message('db.path = {0} db.conn = {1}'.format(db['path'], dir(db['conn'])), True)

	# A pool of threads to execute calls asynchronously.
	# The ping operation is ran from a separate thread (not separate process).
	executor = concurrent.futures.ThreadPoolExecutor(1)
	executor.submit(setup_ping)

	# Start WebSocket server.
	serve_forever()

	# Close database.
	db['conn'].close()



#########################
# Script entry point.
#########################

if __name__ == "__main__":
	main()
