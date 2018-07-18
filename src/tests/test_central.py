import unittest
import signal
import subprocess
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
from time import struct_time, localtime
from uuid import UUID
from pathlib import Path

from netaddr import mac_eui48, EUI
import zmq
import blosc

from archsdn_central.zmq_messages import \
    loads, dumps, \
    RPLSuccess, \
    REQLocalTime, RPLLocalTime, \
    REQCentralNetworkPolicies, RPLCentralNetworkPolicies, \
    REQRegisterController, REQQueryControllerInfo, RPLControllerInformation, REQUnregisterController, \
    REQUpdateControllerInfo, \
    RPLControllerAlreadyRegistered, RPLControllerNotRegistered, REQIsControllerRegistered, \
    RPLIPv6InfoAlreadyRegistered, RPLIPv4InfoAlreadyRegistered, \
    REQRegisterControllerClient, REQRemoveControllerClient, REQIsClientAssociated, REQUnregisterAllClients, \
    REQClientInformation, RPLClientInformation, \
    RPLClientAlreadyRegistered, RPLClientNotRegistered, \
    REQAddressInfo, RPLAddressInfo, \
    RPLAfirmative, RPLNegative, RPLNoResultsAvailable


mac_eui48.word_sep = ":"
database_location = Path("/tmp/test_central.sqlite3")


def openPuppetProcess():
    if Path("../archsdn_central/main.py").exists():
        return subprocess.Popen(
            ("../archsdn_central/main.py", "-l", "DEBUG", "-s", str(database_location))
        )
    if Path("./src/archsdn_central/main.py").exists():
        return subprocess.Popen(
            ("./src/archsdn_central/main.py", "-l", "DEBUG", "-s", str(database_location))
        )
    raise SystemExit("archsdn_central.main.py not found.")


class ZMQ_Puppet_Socket():
    def __init__(self, location="tcp://127.0.0.1:12345"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(location)

    def send(self, obj):
        return self.socket.send(blosc.compress(dumps(obj)))

    def recv(self):
        return loads(blosc.decompress(self.socket.recv(), as_bytearray=True))


class DefaultInitAndClose(unittest.TestCase):
    def setUp(self):
        self.central = openPuppetProcess()
        self.socket = ZMQ_Puppet_Socket()

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()
        database_location.unlink()

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
        self.assertIsInstance(msg.service_reservation_policies, dict)
        self.assertEqual(msg.ipv4_network, IPv4Network("10.0.0.0/8"))
        self.assertEqual(msg.ipv6_network, IPv6Network("fd61:7263:6873:646e::0/64"))
        self.assertEqual(msg.ipv4_service, IPv4Address("10.0.0.1"))
        self.assertEqual(msg.ipv6_service, IPv6Address("fd61:7263:6873:646e::1"))
        self.assertEqual(msg.mac_service, EUI("FE:FF:FF:FF:FF:FF"))
        self.assertEqual(
            msg.service_reservation_policies,
            {"ICMP4": {"bandwidth": 100},"IPv4": {"TCP": {80: 1000}}}
        )
        self.assertLessEqual(msg.registration_date, localtime())


class MultipleClientsOperations(unittest.TestCase):
    def setUp(self):
        self.central = openPuppetProcess()
        self.socket_1 = ZMQ_Puppet_Socket()
        self.socket_2 = ZMQ_Puppet_Socket()

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()
        database_location.unlink()

    def test_multiple_clients(self):
        self.socket_1.send(REQLocalTime())
        self.socket_2.send(REQLocalTime())
        msg_1 = self.socket_1.recv()
        msg_2 = self.socket_2.recv()
        self.assertIsInstance(msg_1, RPLLocalTime)
        self.assertIsInstance(msg_2, RPLLocalTime)


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
        database_location.unlink()

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

    def test_query_controller_information_only_ipv4(self):
        self.socket.send(REQRegisterController(self.uuid, ipv4_info=self.ipv4_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQQueryControllerInfo(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerInformation)

        self.assertEqual(msg.ipv4, self.ipv4_info[0])
        self.assertEqual(msg.ipv4_port, self.ipv4_info[1])
        self.assertEqual(msg.ipv6, None)
        self.assertEqual(msg.ipv6_port, None)
        self.assertEqual(msg.name, ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

    def test_query_controller_information_only_ipv6(self):
        self.socket.send(REQRegisterController(self.uuid, ipv6_info=self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQQueryControllerInfo(self.uuid))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerInformation)

        self.assertEqual(msg.ipv4, None)
        self.assertEqual(msg.ipv4_port, None)
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

    def test_query_address_info(self):
        self.socket.send(REQRegisterController(self.uuid, self.ipv4_info, self.ipv6_info))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

        self.socket.send(REQAddressInfo(ipv4=IPv4Address("192.168.1.1")))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLAddressInfo)
        self.assertEqual(msg.controller_id, self.uuid)
        self.assertEqual(msg.client_id, 0)
        self.assertEqual(msg.name, ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

        self.socket.send(REQAddressInfo(ipv6=IPv6Address(1)))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLAddressInfo)
        self.assertEqual(msg.controller_id, self.uuid)
        self.assertEqual(msg.client_id, 0)
        self.assertEqual(msg.name, ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

    def test_query_address_info_no_results(self):
        self.socket.send(REQAddressInfo(ipv4=IPv4Address("192.168.1.1")))
        self.assertIsInstance(self.socket.recv(), RPLNoResultsAvailable)
        self.socket.send(REQAddressInfo(ipv6=IPv6Address(1)))
        self.assertIsInstance(self.socket.recv(), RPLNoResultsAvailable)


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
        database_location.unlink()

    def test_register_client(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

    def test_query_client_info(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQClientInformation(self.uuid, self.client_id))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLClientInformation)
        self.assertEqual(msg.ipv4, IPv4Address("10.0.0.2"))
        self.assertEqual(msg.ipv6, IPv6Address("fd61:7263:6873:646e::2"))
        self.assertEqual(msg.name, ".".join((str(self.client_id), str(self.uuid), 'archsdn')))

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

    def test_query_address_info(self):
        self.socket.send(REQRegisterControllerClient(self.uuid, self.client_id))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

        self.socket.send(REQAddressInfo(ipv4=IPv4Address("10.0.0.2")))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLAddressInfo)
        self.assertEqual(msg.controller_id, self.uuid)
        self.assertEqual(msg.client_id, self.client_id)
        self.assertEqual(msg.name, ".".join((str(self.client_id), str(self.uuid), 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

        self.socket.send(REQAddressInfo(ipv6=IPv6Address("fd61:7263:6873:646e::2")))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLAddressInfo)
        self.assertEqual(msg.controller_id, self.uuid)
        self.assertEqual(msg.client_id, self.client_id)
        self.assertEqual(msg.name, ".".join((str(self.client_id), str(self.uuid), 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

    def test_query_address_info_no_results(self):
        self.socket.send(REQAddressInfo(ipv4=IPv4Address("10.0.0.2")))
        self.assertIsInstance(self.socket.recv(), RPLNoResultsAvailable)
        self.socket.send(REQAddressInfo(ipv6=IPv6Address("fd61:7263:6873:646e::2")))
        self.assertIsInstance(self.socket.recv(), RPLNoResultsAvailable)


class ControllerRegistrationCornerCases(unittest.TestCase):
    def setUp(self):
        self.central = openPuppetProcess()
        self.socket = ZMQ_Puppet_Socket()

    def tearDown(self):
        self.central.send_signal(signal.SIGINT)
        self.central.wait()
        database_location.unlink()

    def test_query_dual_controller_information_zeros(self):
        self.socket.send(REQRegisterController(UUID(int=1), (IPv4Address("0.0.0.0"), 54321)))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)
        self.socket.send(REQRegisterController(UUID(int=2), (IPv4Address("0.0.0.0"), 54322)))
        self.assertIsInstance(self.socket.recv(), RPLSuccess)

        self.socket.send(REQQueryControllerInfo(UUID(int=1)))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerInformation)

        self.assertEqual(msg.ipv4, IPv4Address("0.0.0.0"))
        self.assertEqual(msg.ipv4_port, 54321)
        self.assertEqual(msg.ipv6, None)
        self.assertEqual(msg.ipv6_port, None)
        self.assertEqual(msg.name, ".".join((str(UUID(int=1)), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())

        self.socket.send(REQQueryControllerInfo(UUID(int=2)))
        msg = self.socket.recv()
        self.assertIsInstance(msg, RPLControllerInformation)

        self.assertEqual(msg.ipv4, IPv4Address("0.0.0.0"))
        self.assertEqual(msg.ipv4_port, 54322)
        self.assertEqual(msg.ipv6, None)
        self.assertEqual(msg.ipv6_port, None)
        self.assertEqual(msg.name, ".".join((str(UUID(int=2)), 'controller', 'archsdn')))
        self.assertLessEqual(msg.registration_date, localtime())