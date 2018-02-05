import unittest
import logging
import sys
import time
import uuid
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address
from netaddr import EUI, mac_eui48
mac_eui48.word_sep = ":"

database_location = ":memory:"
from helpers import custom_logging_callback
import database

sys.excepthook = (lambda tp, val, tb: custom_logging_callback(logging.getLogger(), logging.ERROR, tp, val, tb))


class DefaultInitAndClose(unittest.TestCase):

    def setUp(self):
        database.initialise(location=database_location)

    def tearDown(self):
        database.close()


    def test_get_default_info(self):
        info = database.info()
        self.assertIsInstance(info, dict)
        self.assertIn("ipv4_network", info)
        self.assertIn("ipv6_network", info)
        self.assertIn("ipv4_service", info)
        self.assertIn("ipv6_service", info)
        self.assertIn("mac_service", info)
        self.assertIn("registration_date", info)
        self.assertIsInstance(info["ipv4_network"], IPv4Network)
        self.assertIsInstance(info["ipv6_network"], IPv6Network)
        self.assertIsInstance(info["ipv4_service"], IPv4Address)
        self.assertIsInstance(info["ipv6_service"], IPv6Address)
        self.assertIsInstance(info["mac_service"], EUI)
        self.assertIsInstance(info["registration_date"], time.struct_time)
        self.assertEqual(info["ipv4_network"], IPv4Network("10.0.0.0/8"))
        self.assertEqual(info["ipv6_network"], IPv6Network("fd61:7263:6873:646e::0/64"))
        self.assertEqual(info["ipv4_service"], IPv4Address("10.0.0.1"))
        self.assertEqual(info["ipv6_service"], IPv6Address("fd61:7263:6873:646e::1"))
        self.assertEqual(info["mac_service"], EUI("FE:FF:FF:FF:FF:FF"))
        self.assertLessEqual(info["registration_date"], time.localtime())


class ControllersTests(unittest.TestCase):
    def setUp(self):
        print("setUp")
        database.initialise(location=database_location)
        self.uuid = uuid.UUID(int=1)
        self.ipv4_info = (IPv4Address("192.168.1.1"), 12345)
        self.ipv6_info = (IPv6Address(1), 12345)


    def tearDown(self):
        print("tearDown")
        database.close()


    def test_register_controller(self):
        database.register_controller(self.uuid, ipv4_info=self.ipv4_info)
        info = database.query_controller_info(self.uuid)
        self.assertIsInstance(info, dict)
        self.assertIn("ipv4", info)
        self.assertIn("ipv4_port", info)
        self.assertIn("ipv6", info)
        self.assertIn("ipv6_port", info)
        self.assertIn("name", info)
        self.assertIn("registration_date", info)

        self.assertIsInstance(info["ipv4"], IPv4Address)
        self.assertIsInstance(info["ipv4_port"], int)
        self.assertGreater(info["ipv4_port"], 0)
        self.assertLess(info["ipv4_port"], 0xFFFF)
        self.assertIsInstance(info["name"], str)
        self.assertIsInstance(info['registration_date'], time.struct_time)

        self.assertEqual(info["ipv4"], self.ipv4_info[0])
        self.assertEqual(info["ipv4_port"], self.ipv4_info[1])
        self.assertEqual(info["ipv6"], None)
        self.assertEqual(info["ipv6_port"], None)
        self.assertEqual(info["name"], ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertLessEqual(info['registration_date'], time.localtime(time.time()))

    def test_register_controller_ipv6(self):
        database.register_controller(self.uuid, ipv6_info=self.ipv6_info)
        info = database.query_controller_info(self.uuid)
        self.assertIn("ipv4", info)
        self.assertIn("ipv4_port", info)
        self.assertIn("ipv6", info)
        self.assertIn("ipv6_port", info)
        self.assertIn("name", info)

        self.assertIsInstance(info["ipv6"], IPv6Address)
        self.assertIsInstance(info["ipv6_port"], int)
        self.assertGreater(info["ipv6_port"], 0)
        self.assertLess(info["ipv6_port"], 0xFFFF)
        self.assertIsInstance(info["name"], str)
        self.assertIsInstance(info['registration_date'], time.struct_time)

        self.assertEqual(info["ipv4"], None)
        self.assertEqual(info["ipv4_port"], None)
        self.assertEqual(info["ipv6"], self.ipv6_info[0])
        self.assertEqual(info["ipv6_port"], self.ipv6_info[1])
        self.assertEqual(info["name"], ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertIsInstance(info['registration_date'], time.struct_time)
        self.assertLessEqual(info['registration_date'], time.localtime(time.time()))

    def test_register_controller_ipv4_and_ipv6(self):
        database.register_controller(self.uuid, ipv4_info=self.ipv4_info, ipv6_info=self.ipv6_info)
        info = database.query_controller_info(self.uuid)
        self.assertIn("ipv4", info)
        self.assertIn("ipv4_port", info)
        self.assertIn("ipv6", info)
        self.assertIn("ipv6_port", info)
        self.assertIn("name", info)

        self.assertIsInstance(info["ipv4"], IPv4Address)
        self.assertIsInstance(info["ipv4_port"], int)
        self.assertGreater(info["ipv4_port"], 0)
        self.assertLess(info["ipv4_port"], 0xFFFF)
        self.assertIsInstance(info["ipv6"], IPv6Address)
        self.assertIsInstance(info["ipv6_port"], int)
        self.assertGreater(info["ipv6_port"], 0)
        self.assertLess(info["ipv6_port"], 0xFFFF)
        self.assertIsInstance(info["name"], str)
        self.assertIsInstance(info['registration_date'], time.struct_time)

        self.assertEqual(info["ipv4"], self.ipv4_info[0])
        self.assertEqual(info["ipv4_port"], self.ipv4_info[1])
        self.assertEqual(info["ipv6"], self.ipv6_info[0])
        self.assertEqual(info["ipv6_port"], self.ipv6_info[1])
        self.assertEqual(info["name"], ".".join((str(self.uuid), 'controller', 'archsdn')))
        self.assertIsInstance(info['registration_date'], time.struct_time)
        self.assertLessEqual(info['registration_date'], time.localtime(time.time()))

    def test_register_controller_no_ip(self):
        with self.assertRaises(AssertionError):
            database.register_controller(self.uuid)

    def test_double_registration(self):
        database.register_controller(self.uuid, ipv4_info=self.ipv4_info, ipv6_info=self.ipv6_info)
        with self.assertRaises(database.IPv4InfoAlreadyRegistered):
            database.register_controller(uuid.UUID(int=2), ipv4_info=self.ipv4_info, ipv6_info=(IPv6Address(2), 1))
        with self.assertRaises(database.IPv6InfoAlreadyRegistered):
            database.register_controller(uuid.UUID(int=2), ipv4_info=(IPv4Address("192.168.1.2"), 12345),
                                         ipv6_info=self.ipv6_info)
        with self.assertRaises(database.ControllerAlreadyRegistered):
            database.register_controller(self.uuid, ipv4_info=(IPv4Address("192.168.1.2"), 12345),
                                         ipv6_info=(IPv6Address(2), 1))

    def test_remove_controller(self):
        database.register_controller(self.uuid, ipv4_info=self.ipv4_info, ipv6_info=self.ipv6_info)
        self.assertIsNone(database.remove_controller(self.uuid))
        with self.assertRaises(database.ControllerNotRegistered):
            database.query_controller_info(self.uuid)
        with self.assertRaises(database.ControllerNotRegistered):
            database.remove_controller(self.uuid)


class ClientsTests(unittest.TestCase):
    def setUp(self):
        self.controller_uuid = uuid.UUID(int=1)
        self.client_id = 100
        database.initialise(location=database_location, ipv4_network=IPv4Network("10.0.0.0"))
        database.register_controller(uuid.UUID(int=1), ipv4_info=(IPv4Address("192.168.1.1"), 12345),
                                     ipv6_info=(IPv6Address(1), 12345))

    def tearDown(self):
        database.close()

    def test_register_client(self):
        (ipv4, ipv6, name) = database.register_client(self.client_id, self.controller_uuid)
        self.assertEqual(ipv4, IPv4Address("10.0.0.2"))
        self.assertEqual(ipv6, IPv6Address('fd61:7263:6873:646e::2'))

    def test_double_registration(self):
        database.register_client(self.client_id, self.controller_uuid)
        with self.assertRaises(database.ClientAlreadyRegistered):
            database.register_client(self.client_id, self.controller_uuid)

    def test_query_info(self):
        database.register_client(self.client_id, self.controller_uuid)
        info = database.query_client_info(self.client_id, self.controller_uuid)
        self.assertIn("ipv4", info)
        self.assertIn("ipv6", info)
        self.assertIn("name", info)
        self.assertIn("registration_date", info)
        self.assertEqual(info['ipv4'], IPv4Address("10.0.0.2"))
        self.assertEqual(info['ipv6'], IPv6Address('fd61:7263:6873:646e::2'))
        self.assertEqual(info['name'], ".".join((str(self.client_id), str(self.controller_uuid), "archsdn")))
        self.assertIsInstance(info['registration_date'], time.struct_time)
        self.assertLessEqual(info['registration_date'], time.localtime(time.time()))

    def test_remove_client(self):
        database.register_client(self.client_id, self.controller_uuid)
        self.assertIsNone(database.remove_client(self.client_id, self.controller_uuid))
        with self.assertRaises(database.ClientNotRegistered):
            database.remove_client(self.client_id, self.controller_uuid)

    def test_remove_controller_and_associated_clients(self):
        self.assertIsNone(database.remove_controller(self.controller_uuid))
        with self.assertRaises(database.ControllerNotRegistered):
            database.remove_client(self.client_id, self.controller_uuid)

