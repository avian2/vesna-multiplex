import argparse
import logging
import signal
import socket
import SocketServer
import string
import threading

log = logging.getLogger(__name__)

# defaults
WEST_PORT=2201
WEST_HOST=""

EAST_PORT=2101
EAST_HOST="localhost"

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	allow_reuse_address = True

class MultiSocket(object):
	def __init__(self):
		self.sockets = set()
		self.lock = threading.Lock()

	def num(self):
		return len(self.sockets)

	def add(self, socket):
		assert socket not in self.sockets
		self.lock.acquire()
		self.sockets.add(socket)
		self.lock.release()

	def remove(self, socket):
		self.lock.acquire()
		self.sockets.remove(socket)
		self.lock.release()

	def sendall_one(self, s, string):
		self.lock.acquire()
		s.sendall(string)
		self.lock.release()

	def sendall(self, string):
		self.lock.acquire()
		for s in self.sockets:
			try:
				s.sendall(string)
			except socket.error:
				pass
		self.lock.release()

	def shutdown(self, how):
		self.lock.acquire()
		for s in self.sockets:
			s.shutdown(how)
		self.lock.release()

	def close(self):
		self.lock.acquire()
		for s in self.sockets:
			s.close()
		self.lock.release()

def iterlines(s):
	rest = ""
	while True:
		resp = s.recv(1024)
		if not resp:
			return

		if all(c in string.printable for c in resp):
			# ascii command, buffer by line
			lines = (rest+resp).split('\n')
			for line in lines[:-1]:
				yield line+'\n'

			rest = lines[-1]
		else:
			# looks binary. might be XCP protocol.
			# just send everything
			yield rest+resp
			rest = ''

class TCPOutHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		log.info("[east] connect %s:%d" % self.client_address)

		west_sockets = self.server.m.west_sockets
		east_sockets = self.server.m.east_sockets

		east_sockets.add(conn)

		for cmd in iterlines(conn):
			log.debug("[east] cmd=%r" % (cmd,))

			if cmd.startswith('?'):
				resp = self.command(cmd.strip())
				log.debug("[east] resp=%r" % (resp,))
				east_sockets.sendall_one(conn, resp)
			else:
				west_sockets.sendall(cmd)

		log.info("[east] disconnect %s:%d" % self.client_address)

		east_sockets.remove(conn)

	def command(self, cmd):
		west_sockets = self.server.m.west_sockets
		east_sockets = self.server.m.east_sockets

		if cmd == '?ping':
			return 'ok\n'
		elif cmd == '?count west':
			return '%d\nok\n' % (west_sockets.num(),)
		elif cmd == '?count east':
			return '%d\nok\n' % (east_sockets.num(),)
		else:
			return 'error: unknown multiplexer command %r' % (cmd,)

class TCPInHandler(SocketServer.BaseRequestHandler):
	def handle(self):
		self.reader(self.request)

	def reader(self, conn):
		log.info("[west] connect %s:%d" % self.client_address)

		self.server.m.west_sockets.add(conn)

		while True:
			resp = conn.recv(1024)
			if not resp:
				break

			log.debug("[west] recv=%r" % (resp,))

			self.server.m.east_sockets.sendall(resp)

		log.info("[west] disconnect %s:%d" % self.client_address)

		self.server.m.west_sockets.remove(conn)

class VESNAMultiplex(object):

	def __init__(self, west_port=WEST_PORT, east_port=EAST_PORT, west_host=WEST_HOST, east_host=EAST_HOST):
		self.west_port = west_port
		self.east_port = east_port

		self.west_host = west_host
		self.east_host = east_host

		self.east_sockets = MultiSocket()
		self.west_sockets = MultiSocket()

		self.is_running = threading.Lock()
		self.is_running.acquire()

	def run(self, poll_interval=.5):
		log.info("Listening on: west=%s:%d east=%s:%d" % (self.west_host, self.west_port, self.east_host, self.east_port))
		self.west_server = ThreadingTCPServer((self.west_host, self.west_port), TCPInHandler)
		self.west_server.m = self
		self.east_server = ThreadingTCPServer((self.east_host, self.east_port), TCPOutHandler)
		self.east_server.m = self

		self.west_thread = threading.Thread(target=self.west_server.serve_forever, args=(poll_interval,))
		self.east_thread = threading.Thread(target=self.east_server.serve_forever, args=(poll_interval,))

		self.west_thread.start()
		self.east_thread.start()

		self.is_running.release()

		# allow for signal processing
		while True:
			self.west_thread.join(.2)
			if not self.west_thread.isAlive():
				break

		self.east_thread.join()

		log.info("Closing sockets")

		self.west_sockets.shutdown(socket.SHUT_RDWR)
		self.east_sockets.shutdown(socket.SHUT_RDWR)

		self.west_server.server_close()
		self.east_server.server_close()

		self.west_sockets.close()
		self.east_sockets.close()

		log.info("Stopped")

	def stop(self):
		self.west_server.shutdown()
		self.east_server.shutdown()

def main():
	parser = argparse.ArgumentParser(description="multiplex a TCP connection to multiple clients.")

	parser.add_argument('--west-port', metavar='PORT', type=int, default=WEST_PORT, dest='west_port',
			help="port to listen on for connection from a device")
	parser.add_argument('--west-if', metavar='ADDR', default=WEST_HOST, dest='west_host',
			help="interface to listen on for connection from a device")

	parser.add_argument('--east-port', metavar='PORT', type=int, default=EAST_PORT, dest='east_port',
			help="port to listen on for connections from clients")
	parser.add_argument('--east-if', metavar='ADDR', default=EAST_HOST, dest='east_host',
			help="interface to listen on for connections from clients")

	args = parser.parse_args()

	logging.basicConfig(level=logging.INFO)

	m = VESNAMultiplex(west_port=args.west_port, west_host=args.west_host,
			east_port=args.east_port, east_host=args.east_host)

	def handler(signum, frame):
		log.warning("Signal %d caught! Stopping..." % (signum,))
		m.stop()

	signal.signal(signal.SIGTERM, handler)
	signal.signal(signal.SIGINT, handler)

	m.run()

if __name__ == "__main__":
	main()
