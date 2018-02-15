import unittest
import signal
import subprocess
import pickle
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from time import struct_time, localtime
from uuid import UUID, uuid4

from netaddr import mac_eui48, EUI
import zmq
import blosc

from zmq_messages import \
    RPLSuccess, RPLGenericError, \
    REQLocalTime, RPLLocalTime, \
    REQCentralNetworkPolicies, RPLCentralNetworkPolicies, \
    REQRegisterController, REQQueryControllerInfo, RPLControllerInformation, REQUnregisterController, \
    REQUpdateControllerInfo, \
    RPLControllerAlreadyRegistered, RPLControllerNotRegistered, REQIsControllerRegistered, \
    RPLIPv6InfoAlreadyRegistered, RPLIPv4InfoAlreadyRegistered, \
    REQRegisterControllerClient, REQRemoveControllerClient, REQIsClientAssociated, REQUnregisterAllClients, \
    RPLClientAlreadyRegistered, RPLClientNotRegistered, \
    RPLAfirmative, RPLNegative


mac_eui48.word_sep = ":"
database_location = ":memory:"


def openPuppetProcess():
    return subprocess.Popen(("python3", "-d", "main.py", "-l", "DEBUG"), close_fds=True)


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
        self.central = openPuppetProcess()
        self.socket = ZMQ_Puppet_Socket()

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()

    def test_get_default_info(self):
        self.socket.send(REQLocalTime())
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLLocalTime)

    def test_get_central_network_info(self):
        self.socket.send(REQCentralNetworkPolicies())
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLCentralNetworkPolicies)
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
        self.central = openPuppetProcess()
        self.socket = ZMQ_Puppet_Socket()

        self.uuid = UUID(int=1)
        self.ipv4_info = (IPv4Address("192.168.1.1"), 12345)
        self.ipv6_info = (IPv6Address(1), 12345)

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()

    def test_register_controller(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def test_query_controller_information(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQQueryControllerInfo(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerInformation)

        self.assertEqual(msg.ipv4, self.ipv4_info[0])
        self.assertEqual(msg.ipv4_port, self.ipv4_info[1])
        self.assertEqual(msg.ipv6, self.ipv6_info[0])
        self.assertEqual(msg.ipv6_port, self.ipv6_info[1])
        self.assertEqual(msg.name, ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

    def test_remove_controller(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQUnregisterController(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, msg="{:s}".format(str(msg)))

    def test_remove_non_existent_controller(self):
        self.socket.send(REQUnregisterController(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerNotRegistered)

    def test_query_info_non_existent_controller(self):
        self.socket.send(REQQueryControllerInfo(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerNotRegistered, msg="{:s}".format(str(msg)))

    def test_query_info_previously_removed_existent_controller(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQUnregisterController(self.uuid))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQQueryControllerInfo(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerNotRegistered)

    def test_duplicate_register_controller_attempt(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLControllerAlreadyRegistered)

    def test_duplicate_ipv4_register_attempt(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(
            REQRegisterController(UUID(int=2), self.ipv4_info, (IPv6Address("fd61:7263:6873:646e::ff"), 12345))
        )
        self.assertIsInstance(self.socket.recv(), RPLIPv4InfoAlreadyRegistered)

    def test_duplicate_ipv6_register_attempt(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQRegisterController(UUID(int=2), (IPv4Address("10.0.0.10"), 12345), self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLIPv6InfoAlreadyRegistered)

    def test_check_controller_is_registered(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQIsControllerRegistered(self.uuid))
        self.assertIsInstance(self.socket.recv(), RPLAfirmative)

    def test_check_controller_is_not_registered(self):
        self.socket.send(REQIsControllerRegistered(UUID(int=2)))
        self.assertIsInstance(self.socket.recv(), RPLNegative)

    def test_update_controller_ipv4(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQUpdateControllerInfo(self.uuid, ipv4_info=(IPv4Address("192.168.1.10"), 12345)))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def test_update_controller_ipv6(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQUpdateControllerInfo(self.uuid, ipv6_info=(IPv6Address("fd61:7263:6873:646e::ff"), 12345)))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def test_update_controller_ipv4_and_ipv6(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(
            REQUpdateControllerInfo(
                self.uuid,
                ipv4_info=(IPv4Address("10.0.0.10"), 12345),
                ipv6_info=(IPv6Address("fd61:7263:6873:646e::ff"), 12345)
            )
        )
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def test_duplicate_controller_ipv4_update(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQUpdateControllerInfo(self.uuid, ipv4_info=(IPv4Address("192.168.1.1"), 12345)))
        self.assertIsInstance(self.socket.recv(), RPLIPv4InfoAlreadyRegistered)

    def test_duplicate_controller_ipv6_update(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQUpdateControllerInfo(self.uuid, ipv6_info=(IPv6Address(1), 12345)))
        self.assertIsInstance(self.socket.recv(), RPLIPv6InfoAlreadyRegistered)


class ClientsRegistration(unittest.TestCase):
    def setUp(self):
        self.central = openPuppetProcess()
        self.socket = ZMQ_Puppet_Socket()

        self.uuid = UUID(int=1)
        self.ipv4_info = (IPv4Address("192.168.1.1"), 12345)
        self.ipv6_info = (IPv6Address(1), 12345)
        self.client_id = 2
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()

    def test_register_client(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def test_remove_client(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, str(msg))
        self.socket.send(REQRemoveControllerClient(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, str(msg))

    def test_duplicate_client_registration(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, str(msg))
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLClientAlreadyRegistered, str(msg))

    def test_remove_unregistered_client(self):
        self.socket.send(REQRemoveControllerClient(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLClientNotRegistered, str(msg))

    def test_register_client_with_unregistered_controller(self):
        self.socket.send(REQRegisterControllerClient(UUID(int=2), self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerNotRegistered, str(msg))

    def test_check_for_client_registration(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQIsClientAssociated(self.uuid, self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLAfirmative)
        self.socket.send(REQIsClientAssociated(self.uuid, 3))
        self.assertIsInstance(self.socket.recv(), RPLNegative)

    def test_check_for_client_registration_with_unregistered_controller(self):
        self.socket.send(REQIsClientAssociated(UUID(int=2), self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLControllerNotRegistered)

    def test_clean_all_registered_clients(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, str(msg))
        self.socket.send(REQRegisterControllerClient(self.uuid, 3))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, str(msg))

        self.socket.send(REQUnregisterAllClients(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLSuccess, str(msg))