import unittest
import signal
import subprocess
import pickle
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from time import struct_time, localtime
from uuid import UUID

from netaddr import mac_eui48, EUI
import zmq
import blosc

from zmq_messages import \
    RPL_Success, RPL_Error, \
    REQ_LocalTime, RPL_LocalTime, \
    REQ_CentralNetworkPolicies, RPL_CentralNetworkPolicies, \
    REQ_Register_Controller, REQ_Query_Controller_Info, RPL_ControllerInformation


mac_eui48.word_sep = ":"
database_location = ":memory:"


class ZMQ_Puppet_Socket():
    def __init__(self, location="tcp://127.0.0.1:12345"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(location)

    def send(self, obj):
        return self.socket.send(blosc.compress(pickle.dumps(obj)))

    def recv(self):
        return pickle.loads(blosc.decompress(self.socket.recv(), as_bytearray=True))


class DefaultInitAndClose(unittest.TestCase):
    def setUp(self):
        self.central = subprocess.Popen("./main.py", close_fds=True)
        self.socket = ZMQ_Puppet_Socket()

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()

    def test_get_default_info(self):
        self.socket.send(REQ_LocalTime())
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPL_LocalTime)

    def test_get_central_network_info(self):
        self.socket.send(REQ_CentralNetworkPolicies())
        msg = self.socket.recv()
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


class ControllerRegistration(unittest.TestCase):
    def setUp(self):
        self.central = subprocess.Popen("./main.py", close_fds=True)
        self.socket = ZMQ_Puppet_Socket()

        self.uuid = UUID(int=1)
        self.ipv4_info = (IPv4Address("192.168.1.1"), 12345)
        self.ipv6_info = (IPv6Address(1), 12345)

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()

    def test_register_controller(self):
        self.socket.send(REQ_Register_Controller(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPL_Success)

    def test_query_controller_information(self):
        self.socket.send(REQ_Register_Controller(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPL_Success)
        self.socket.send(REQ_Query_Controller_Info(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPL_ControllerInformation)

        self.assertEqual(msg.ipv4, self.ipv4_info[0])
        self.assertEqual(msg.ipv4_port, self.ipv4_info[1])
        self.assertEqual(msg.ipv6, self.ipv6_info[0])
        self.assertEqual(msg.ipv6_port, self.ipv6_info[1])
        self.assertEqual(msg.name, ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())


