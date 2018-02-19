import unittest
import logging
import sys
import asyncio
import time
import uuid
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address
from netaddr import EUI, mac_eui48

from archsdn_central.helpers import custom_logging_callback
from archsdn_central import database

mac_eui48.word_sep = ":"
database_location = ":memory:"

sys.excepthook = (lambda tp, val, tb: custom_logging_callback(logging.getLogger(), logging.ERROR, tp, val, tb))
loop = asyncio.get_event_loop()


class DefaultInitAndClose(unittest.TestCase):

    def setUp(self):
        fut = database.initialise(location=database_location)
        loop.run_until_complete(fut)

    def tearDown(self):
        fut = database.close()
        loop.run_until_complete(fut)

    def test_get_default_info(self):
        fut = database.info()
        loop.run_until_complete(fut)
        info = fut.result()
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
        fut = database.initialise(location=database_location)
        loop.run_until_complete(fut)
        self.uuid = uuid.UUID(int=1)
        self.ipv4_info = (IPv4Address("192.168.1.1"), 12345)
        self.ipv6_info = (IPv6Address(1), 12345)

    def tearDown(self):
        fut = database.close()
        loop.run_until_complete(fut)

    def test_register_controller(self):
        fut = database.register_controller(self.uuid, ipv4_info=self.ipv4_info)
        loop.run_until_complete(fut)
        fut = database.query_controller_info(self.uuid)
        loop.run_until_complete(fut)
        info = fut.result()

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
        fut = database.register_controller(self.uuid, ipv6_info=self.ipv6_info)
        loop.run_until_complete(fut)
        fut = database.query_controller_info(self.uuid)
        loop.run_until_complete(fut)
        info = fut.result()

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
        fut = database.register_controller(self.uuid, ipv4_info=self.ipv4_info, ipv6_info=self.ipv6_info)
        loop.run_until_complete(fut)
        fut = database.query_controller_info(self.uuid)
        loop.run_until_complete(fut)
        info = fut.result()

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
            fut = database.register_controller(self.uuid)
            loop.run_until_complete(fut)
            fut.result()

    def test_double_registration(self):
        fut = database.register_controller(self.uuid, ipv4_info=self.ipv4_info, ipv6_info=self.ipv6_info)
        loop.run_until_complete(fut)

        with self.assertRaises(database.IPv4InfoAlreadyRegistered):
            fut = database.register_controller(uuid.UUID(int=2), ipv4_info=self.ipv4_info, ipv6_info=(IPv6Address(2), 1))
            loop.run_until_complete(fut)
            fut.result()
        with self.assertRaises(database.IPv6InfoAlreadyRegistered):
            fut = database.register_controller(uuid.UUID(int=2), ipv4_info=(IPv4Address("192.168.1.2"), 12345),
                                         ipv6_info=self.ipv6_info)
            loop.run_until_complete(fut)
            fut.result()
        with self.assertRaises(database.ControllerAlreadyRegistered):
            fut = database.register_controller(self.uuid, ipv4_info=(IPv4Address("192.168.1.2"), 12345),
                                         ipv6_info=(IPv6Address(2), 1))
            loop.run_until_complete(fut)
            fut.result()

    def test_remove_controller(self):
        fut = database.register_controller(self.uuid, ipv4_info=self.ipv4_info, ipv6_info=self.ipv6_info)
        loop.run_until_complete(fut)

        fut = database.remove_controller(self.uuid)
        loop.run_until_complete(fut)

        self.assertIsNone(fut.result())
        with self.assertRaises(database.ControllerNotRegistered):
            fut = database.query_controller_info(self.uuid)
            loop.run_until_complete(fut)
            fut.result()
        with self.assertRaises(database.ControllerNotRegistered):
            fut = database.remove_controller(self.uuid)
            loop.run_until_complete(fut)
            fut.result()


class ClientsTests(unittest.TestCase):
    def setUp(self):
        self.controller_uuid = uuid.UUID(int=1)
        self.client_id = 100
        fut = database.initialise(location=database_location, ipv4_network=IPv4Network("10.0.0.0"))
        loop.run_until_complete(fut)
        fut = database.register_controller(
            uuid.UUID(int=1),
            ipv4_info=(IPv4Address("192.168.1.1"), 12345),
            ipv6_info=(IPv6Address(1), 12345)
        )
        loop.run_until_complete(fut)

    def tearDown(self):
        fut = database.close()
        loop.run_until_complete(fut)

    def test_register_client(self):
        fut = database.register_client(self.client_id, self.controller_uuid)
        loop.run_until_complete(fut)
        (ipv4, ipv6, name) = fut.result()

        self.assertEqual(ipv4, IPv4Address("10.0.0.2"))
        self.assertEqual(ipv6, IPv6Address('fd61:7263:6873:646e::2'))

    def test_double_registration(self):
        fut = database.register_client(self.client_id, self.controller_uuid)
        loop.run_until_complete(fut)
        with self.assertRaises(database.ClientAlreadyRegistered):
            fut = database.register_client(self.client_id, self.controller_uuid)
            loop.run_until_complete(fut)
            fut.result()

    def test_query_info(self):
        fut = database.register_client(self.client_id, self.controller_uuid)
        loop.run_until_complete(fut)
        fut = database.query_client_info((self.controller_uuid, self.client_id))
        loop.run_until_complete(fut)
        info = fut.result()
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
        fut = database.register_client(self.client_id, self.controller_uuid)
        loop.run_until_complete(fut)
        fut = database.remove_client(self.client_id, self.controller_uuid)
        loop.run_until_complete(fut)
        self.assertIsNone(fut.result())
        with self.assertRaises(database.ClientNotRegistered):
            fut = database.remove_client(self.client_id, self.controller_uuid)
            loop.run_until_complete(fut)
            fut.result()

    def test_remove_controller_and_associated_clients(self):
        fut = database.remove_controller(self.controller_uuid)
        loop.run_until_complete(fut)
        self.assertIsNone(fut.result())
        with self.assertRaises(database.ControllerNotRegistered):
            fut = database.remove_client(self.client_id, self.controller_uuid)
            loop.run_until_complete(fut)
            fut.result()

