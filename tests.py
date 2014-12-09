import logging
import serial
import socket
import tcp_multiplex
import threading
import time
import unittest

#logging.basicConfig(level=logging.DEBUG)

class TestTcpMultiplexConnection(unittest.TestCase):

	def setUp(self):
		self.m = tcp_multiplex.TcpMultiplex(in_host='localhost')
		self.t = threading.Thread(target=self.m.run, args=(.1,))
		self.t.start()

		self.m.is_running.acquire()

	def _in_comm(self):
		return serial.serial_for_url("socket://localhost:2102", timeout=60)

	def _out_comm(self):
		return serial.serial_for_url("socket://localhost:2101", timeout=60)

	def tearDown(self):
		self.m.stop()
		self.t.join()

	def _test_ping(self, N):

		comm = [ self._out_comm() for n in xrange(N) ]

		for c in comm:
			c.write("?ping\n")

		for c in comm:
			resp = c.readline()
			self.assertEqual("ok\n", resp)

	def test_ping(self):
		self._test_ping(1)

	def test_ping_many(self):
		self._test_ping(5)

	def test_info(self):
		comm_in = self._in_comm()
		comm_out = self._out_comm()

		comm_out.write("?nin\n")
		resp = comm_out.readline()
		self.assertEqual(resp, '1\n')

		comm_out.write("?nout\n")
		resp = comm_out.readline()
		self.assertEqual(resp, '1\n')

	def _test_in_out(self, N):
		comm_in = self._in_comm()

		comm_out = [ self._out_comm() for n in xrange(N) ]

		time.sleep(.1)

		comm_in.write("DS\n")

		for c in comm_out:
			resp = c.readline()
			self.assertEqual("DS\n", resp)

	def test_in_out(self):
		self._test_in_out(1)

	def test_in_out_many(self):
		self._test_in_out(5)

	def _test_out_in(self, N):
		comm_in = self._in_comm()

		comm_out = [ self._out_comm() for n in xrange(N) ]

		comm_out[0].write("version\n")

		resp = comm_in.readline()
		self.assertEqual("version\n", resp)

	def test_out_in(self):
		self._test_out_in(1)

	def test_out_in_many(self):
		self._test_out_in(5)

	def test_out_in_close(self):
		N = 5

		comm_in = self._in_comm()
		comm_out = [ self._out_comm() for n in xrange(N) ]

		time.sleep(1)

		comm_in.write("DS 1\n")
		for c in comm_out:
			resp = c.readline()

		comm_out[0].close()

		comm_in.write("DS 2\n")
		for c in comm_out[1:]:
			resp = c.readline()
			self.assertEqual("DS 2\n", resp)

class TestTcpMultiplexStatic(unittest.TestCase):

	def xest_reader_ping(self):
		m = tcp_multiplex.TcpMultiplex()

		class MockConn:
			def __init__(self):
				self.cnt = -1
				self.b = ""

			def recv(self, n):
				self.cnt += 1
				if self.cnt == 0:
					return "?ping\n"
				else:
					m.stop()
					raise socket.timeout

			def send(self, b):
				self.b += b

		c = MockConn()
		m.reader(c)

		self.assertEqual("ok\n", c.b)

if __name__ == '__main__':
	unittest.main()
