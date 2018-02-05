import unittest
import time
import uuid
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address
import signal

from netaddr import EUI, mac_eui48
mac_eui48.word_sep = ":"

database_location = ":memory:"
import subprocess

import database

class DefaultInitAndClose(unittest.TestCase):
    def setUp(self):
        self.central = subprocess.Popen("./main.py", close_fds=True)


    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()

    def test_get_default_info(self):
        import zmq

        context = zmq.Context()

        #  Socket to talk to server
        print("Connecting to hello world server…")
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:12345")

        #  Do 10 requests, waiting each time for a response
        for request in range(10):
            print("Sending request %s …" % request)
            socket.send(b"Hello")

            #  Get the reply.
            message = socket.recv()
            print("Received reply %s [ %s ]" % (request, message))



