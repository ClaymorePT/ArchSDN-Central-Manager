import logging
import sqlite3
import time
from uuid import UUID
from contextlib import closing
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address

from archsdn_central.helpers import logger_module_name

from .shared_data import GetConnector
from .exceptions import ControllerNotRegistered, ClientNotRegistered, ClientAlreadyRegistered, NoResultsAvailable

__log = logging.getLogger(logger_module_name(__file__))


def register(client_id, controller_uuid):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(client_id, int), "client_id expected to be an instance of type int"
    assert client_id >= 0, "client_id cannot be negative"
    assert isinstance(controller_uuid, UUID), "controller expected to be an instance of type uuid.UUID"

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
            return

    except sqlite3.IntegrityError as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        if "names.name" in ex.args[0]:
            raise ClientAlreadyRegistered()
        raise ex
    except Exception as ex:
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def info(client_id, controller_id):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(controller_id, UUID), \
        "uuid is not a uuid.UUID object instance: {:s}".format(repr(controller_id))
    assert isinstance(client_id, int), "client_id is not a int object instance: {:s}".format(repr(client_id))
    assert 0 < client_id < 0xFFFFFFFF, "client_id value is invalid: value {:d}".format(client_id)

    with closing(GetConnector().cursor()) as db_cursor:
        db_cursor.execute("SELECT ipv4, ipv6, name, registration_date FROM clients_view WHERE "
                          "(clients_view.id == ?) AND (clients_view.controller == ?)", (client_id, controller_id.bytes))

        res = db_cursor.fetchone()
        if not res:
            raise ClientNotRegistered()

        return {
            "ipv4": IPv4Address(res[0]) if res[0] else None,
            "ipv6": IPv6Address(res[1]) if res[1] else None,
            "name": res[2],
            "registration_date": time.localtime(res[3]),
        }


def remove(client_id, controller):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(client_id, int), "clientid expected to be an instance of type int"
    assert client_id >= 0, "clientid cannot be negative"
    assert isinstance(controller, UUID), "controller expected to be an instance of type uuid.UUID"

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
    assert isinstance(controller, UUID), "controller expected to be an instance of type uuid.UUID"

    with closing(GetConnector().cursor()) as db_cursor:
        db_cursor.execute("SELECT id FROM controllers WHERE uuid == ?", (controller.bytes,))

        res = db_cursor.fetchone()
        if res is None:
            raise ControllerNotRegistered()

        db_cursor.execute("SELECT count(id) FROM clients_view WHERE (id == ?) AND (controller == ?)", (client_id, controller.bytes))

        if db_cursor.fetchone()[0] == 0:
            return False
        return True


def query_address_info(ipv4=None, ipv6=None):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert not ((ipv4 is None) and (ipv6 is None)), "ipv4 and ipv6 cannot be null at the same time"
    assert isinstance(ipv4, IPv4Address) or ipv4 is None, "ipv4 is invalid"
    assert isinstance(ipv6, IPv6Address) or ipv6 is None, "ipv6 is invalid"

    with closing(GetConnector().cursor()) as db_cursor:
        db_cursor.execute(
            "SELECT uuid, name, registration_date FROM controllers_view WHERE (ipv4 == ?) OR (ipv6 == ?)",
            (
                int(ipv4) if ipv4 else None,
                ipv6.packed if ipv6 else None
            )
        )

        res = db_cursor.fetchone()
        if res:
            return {
                "controller_id": UUID(bytes=res[0]),
                "client_id": 0,
                "name": res[1],
                "registration_date": time.localtime(res[2])
            }

        db_cursor.execute(
            "SELECT id, controller, name, registration_date FROM clients_view WHERE (ipv4 == ?) OR (ipv6 == ?)",
            (
                int(ipv4) if ipv4 else None,
                ipv6.packed if ipv6 else None
            )
        )

        res = db_cursor.fetchone()
        if res:
            return {
                "client_id": res[0],
                "controller_id": UUID(bytes=res[1]),
                "name": res[2],
                "registration_date": time.localtime(res[3])
            }
        raise NoResultsAvailable()

