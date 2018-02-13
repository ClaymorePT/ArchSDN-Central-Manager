import unittest
import signal
import subprocess
import pickle
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from time import struct_time, localtime

from netaddr import mac_eui48, EUI

from zmq_messages import \
    REQ_LocalTime, RPL_LocalTime, \
    REQ_CentralNetworkPolicies, RPL_CentralNetworkPolicies


#import database

mac_eui48.word_sep = ":"
database_location = ":memory:"


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
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:12345")

        socket.send(pickle.dumps(REQ_LocalTime()))
        #  Get the reply.
        msg = pickle.loads(socket.recv())
        self.assertIsInstance(msg, RPL_LocalTime)

    def test_get_central_network_info(self):
        import zmq

        context = zmq.Context()

        #  Socket to talk to server
        print("Connecting to hello world server…")
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://127.0.0.1:12345")

        socket.send(pickle.dumps(REQ_CentralNetworkPolicies()))
        #  Get the reply.
        msg = pickle.loads(socket.recv())
        self.assertIsInstance(msg, RPL_CentralNetworkPolicies)
        self.assertIsInstance(msg.ipv4_network, IPv4Network)
        self.assertIsInstance(msg.ipv6_network, IPv6Network)
        self.assertIsInstance(msg.ipv4_service, IPv4Address)
        self.assertIsInstance(msg.ipv6_service, IPv6Address)
        self.assertIsInstance(msg.mac_service, EUI)
        self.assertIsInstance(msg.registration_date, struct_time)
        self.assertEqual(msg.ipv4_network, IPv4Network("10.0.0.0/8"))
        self.assertEqual(msg.ipv6_network, IPv6Network("fd61:7263:6873:646e::0/64"))
        self.assertEqual(msg.ipv4_service, IPv4Address("10.0.0.1"))
        self.assertEqual(msg.ipv6_service, IPv6Address("fd61:7263:6873:646e::1"))
        self.assertEqual(msg.mac_service, EUI("FE:FF:FF:FF:FF:FF"))
        self.assertLessEqual(msg.registration_date, localtime())



