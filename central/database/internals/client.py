import logging
import sqlite3
import uuid
import time
from contextlib import closing
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address

from helpers import logger_module_name

from .shared_data import GetConnector
from .exceptions import ControllerNotRegistered, ClientNotRegistered, ClientAlreadyRegistered

__log = logging.getLogger(logger_module_name(__file__))


def register(client_id, controller_uuid):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(client_id, int), "client_id expected to be an instance of type int"
    assert client_id >= 0, "client_id cannot be negative"
    assert isinstance(controller_uuid, uuid.UUID), "controller expected to be an instance of type uuid.UUID"

    try:
        database_connector = GetConnector()
        with closing(database_connector.cursor()) as db_cursor:
            db_cursor.execute("SELECT id FROM controllers WHERE uuid == ?", (controller_uuid.bytes,))

            res = db_cursor.fetchone()
            if res is None:
                raise ControllerNotRegistered()
            controller_id = res[0]

            db_cursor.execute("SELECT ipv4_network, ipv6_network FROM configurations")
            res = db_cursor.fetchone()
            ipv4_network = IPv4Network(res[0])
            ipv6_network = IPv6Network(res[1])

            # Generating a private IPv4 for a new client registration
            db_cursor.execute("SELECT max(id) FROM clients_ipv4s")
            res = db_cursor.fetchone()[0]
            if res:
                if res == ipv4_network.num_addresses:
                    ipv4_id = 1
                    while True:
                        db_cursor.execute("SELECT count(id) FROM clients_ipv4s WHERE id == ?", (ipv4_id,))
                        res = db_cursor.fetchone()[0]
                        if not res:
                            break
                        ipv4_id += 1
                else:
                    ipv4_id = res+1
            else:
                ipv4_id = 1

            ipv4_address = ipv4_network.network_address + ipv4_id
            db_cursor.execute("INSERT INTO clients_ipv4s(id, address) VALUES (?,?)", (ipv4_id, int(ipv4_address),))

            # Generating a private IPv6 for a new client registration
            db_cursor.execute("SELECT max(id) FROM clients_ipv6s")
            res = db_cursor.fetchone()[0]
            if res:
                if res == ipv6_network.num_addresses:
                    ipv6_id = 1
                    while True:
                        db_cursor.execute("SELECT count(id) FROM clients_ipv6s WHERE id == ?", (ipv6_id,))
                        res = db_cursor.fetchone()[0]
                        if not res:
                            break
                        ipv6_id += 1
                else:
                    ipv6_id = res+1
            else:
                ipv6_id = 1

            ipv6_address = ipv6_network.network_address + ipv6_id
            db_cursor.execute("INSERT INTO clients_ipv6s(id, address) VALUES (?,?)", (ipv6_id, ipv6_address.packed,))

            hostname = (".".join((str(client_id), str(controller_uuid), "archsdn")))
            db_cursor.execute("INSERT INTO names(name) "
                              "VALUES (?)", (hostname,))
            name_id = db_cursor.lastrowid

            db_cursor.execute("INSERT INTO clients(id, controller, ipv4, ipv6, name) VALUES (?,?,?,?,?)",
                              (client_id,
                               controller_id,
                               ipv4_id,
                               ipv6_id,
                               name_id
                               )
                              )
            database_connector.commit()
            assert not GetConnector().in_transaction, "database with active transaction"
            return (ipv4_address, ipv6_address, hostname)

    except sqlite3.IntegrityError as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        if "names.name" in ex.args[0]:
            raise ClientAlreadyRegistered()
        raise ex
    except Exception as ex:
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def info(location=None, ipv4=None, ipv6=None):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(location, (tuple, type(None))), "location type is not tuple or None"
    assert location is None or len(location) == 2, "location length is not 2"
    assert location is None or isinstance(location[0], uuid.UUID), "location 1st element type is not UUID"
    assert location is None or isinstance(location[1], int), "location 2nd element type is not int"
    assert location is None or location[1] is None or location[1] >= 0, "location 2nd element cannot be negative"
    assert isinstance(ipv4, (IPv4Address, type(None))), "ipv4 type is not IPv4Address or None"
    assert isinstance(ipv6, (IPv6Address, type(None))), "ipv6 type is not IPv6Address or None"
    assert sum(tuple(
        (i is not None for i in (location, ipv4, ipv6)))) == 1, \
        "can only use one argument (location, ipv4 and ipv6) at a time"

    with closing(GetConnector().cursor()) as db_cursor:
        if location:
            controller = location[0]
            client_id = location[1]

            db_cursor.execute("SELECT ipv4, ipv6, name, registration_date FROM clients_view WHERE "
                              "(clients_view.id == ?) AND (clients_view.controller == ?)", (client_id, controller.bytes))

            res = db_cursor.fetchone()
            if not res:
                raise ClientNotRegistered()

            return {
                "ipv4": IPv4Address(res[0]) if res[0] else None,
                "ipv6": IPv6Address(res[1]) if res[1] else None,
                "name": res[2],
                "registration_date": time.localtime(res[3]),
            }

        elif ipv4:
            db_cursor.execute("SELECT id, controller, ipv6, name, registration_date FROM clients_view WHERE "
                              "(clients_view.ipv4 == ?)", (int(ipv4),))

            res = db_cursor.fetchone()
            if not res:
                raise ClientNotRegistered()

            return {
                "client_id": res[0],
                "controller_id": uuid.UUID(bytes=res[1]),
                "ipv6": IPv6Address(res[2]) if res[2] else None,
                "name": res[3],
                "registration_date": time.localtime(res[4]),
            }

        elif ipv6:
            db_cursor.execute("SELECT id, controller, ipv4, name, registration_date FROM clients_view WHERE "
                              "(clients_view.ipv6 == ?)", (ipv6.packed,))

            res = db_cursor.fetchone()
            if not res:
                raise ClientNotRegistered()

            return {
                "client_id": res[0],
                "controller_id": uuid.UUID(bytes=res[1]),
                "ipv4": IPv4Address(res[2]) if res[2] else None,
                "name": res[3],
                "registration_date": time.localtime(res[4]),
            }




def remove(client_id, controller):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(client_id, int), "clientid expected to be an instance of type int"
    assert client_id >= 0, "clientid cannot be negative"
    assert isinstance(controller, uuid.UUID), "controller expected to be an instance of type uuid.UUID"

    try:
        database_connector = GetConnector()
        with closing(database_connector.cursor()) as db_cursor:
            db_cursor.execute("SELECT id FROM controllers WHERE uuid == ?", (controller.bytes,))

            res = db_cursor.fetchone()
            if res is None:
                raise ControllerNotRegistered()
            controller_id = res[0]

            db_cursor.execute("DELETE FROM clients "
                              "WHERE (clients.id == ?) AND (clients.controller == ?)", (client_id, controller_id))

            database_connector.commit()
            assert not GetConnector().in_transaction, "database with active transaction"
            if db_cursor.rowcount == 0:
                raise ClientNotRegistered()

    except Exception as ex:
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def exists(client_id, controller):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(client_id, int), "clientid expected to be an instance of type int"
    assert client_id >= 0, "clientid cannot be negative"
    assert isinstance(controller, uuid.UUID), "controller expected to be an instance of type uuid.UUID"

    with closing(GetConnector().cursor()) as db_cursor:
        db_cursor.execute("SELECT id FROM controllers WHERE uuid == ?", (controller.bytes,))

        res = db_cursor.fetchone()
        if res is None:
            raise ControllerNotRegistered()

        db_cursor.execute("SELECT count(id) FROM clients_view WHERE (id == ?) AND (controller == ?)", (client_id, controller.bytes))

        if db_cursor.fetchone()[0] == 0:
            return False
        return True

