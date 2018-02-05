import logging
import sqlite3
import time
from contextlib import closing
from uuid import UUID
from ipaddress import IPv4Address, IPv6Address

from helpers import logger_module_name

from .data_validation import is_ipv4_port_tuple, is_ipv6_port_tuple
from .exceptions import ControllerNotRegistered, IPv4InfoAlreadyRegistered, IPv6InfoAlreadyRegistered, \
    ControllerAlreadyRegistered
from .shared_data import GetConnector

__log = logging.getLogger(logger_module_name(__file__))


def register(uuid, ipv4_info=None, ipv6_info=None):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(uuid, UUID), "uuid is not a uuid.UUID object instance"
    assert not ((ipv4_info is None) and (ipv6_info is None)), "ipv4_info and ipv6_info cannot be null at the same time"
    assert is_ipv4_port_tuple(ipv4_info) or ipv4_info is None, "ipv4_info is invalid"
    assert is_ipv6_port_tuple(ipv6_info) or ipv6_info is None, "ipv6_info is invalid"

    try:
        database_connector = GetConnector()
        with closing(database_connector.cursor()) as db_cursor:
            db_cursor.execute("SELECT count(*) FROM controllers "
                              "WHERE controllers.uuid == ?", (uuid.bytes,))
            res = db_cursor.fetchone()
            if res[0] == 1:
                assert not GetConnector().in_transaction, "database with active transaction"
                raise ControllerAlreadyRegistered()

            ipv4_id = None
            if ipv4_info:
                db_cursor.execute("INSERT INTO controllers_ipv4s(address, port) "
                                  "VALUES (?,?)", (int(ipv4_info[0]), ipv4_info[1]))
                ipv4_id = db_cursor.lastrowid

            ipv6_id = None
            if ipv6_info:
                db_cursor.execute("INSERT INTO controllers_ipv6s(address, port) "
                                  "VALUES (?,?)", (ipv6_info[0].packed, ipv6_info[1]))
                ipv6_id = db_cursor.lastrowid

            db_cursor.execute("INSERT INTO names(name) "
                              "VALUES (?)", (".".join((str(uuid), "controller", "archsdn")),))
            name_id = db_cursor.lastrowid

            db_cursor.execute("INSERT INTO controllers(name, ipv4, ipv6, uuid) "
                              "VALUES (?,?,?,?)", (name_id, ipv4_id, ipv6_id, uuid.bytes))
            host_id = db_cursor.lastrowid
            database_connector.commit()
            assert not GetConnector().in_transaction, "database with active transaction"
            return host_id

    except sqlite3.IntegrityError as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        if "controllers_ipv4s.address, controllers_ipv4s.port" in ex.args[0]:
            raise IPv4InfoAlreadyRegistered()
        if "controllers_ipv6s.address, controllers_ipv6s.port" in ex.args[0]:
            raise IPv6InfoAlreadyRegistered()
        if "names.name" in ex.args[0]:
            raise ControllerAlreadyRegistered()
        raise ex
    except Exception as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def infos(uuid):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(uuid, UUID), "uuid is not a uuid.UUID object instance"

    try:
        with closing(GetConnector().cursor()) as db_cursor:
            db_cursor.execute("SELECT ipv4, ipv4_port, ipv6, ipv6_port, name, registration_date  FROM controllers_view "
                              "WHERE controllers_view.uuid == ?", (uuid.bytes,))
            res = db_cursor.fetchone()
            if not res:
                assert not GetConnector().in_transaction, "database with active transaction"
                raise ControllerNotRegistered()

            return {'ipv4': IPv4Address(res[0]) if res[0] else None,
                    'ipv4_port': res[1],
                    'ipv6': IPv6Address(res[2]) if res[2] else None,
                    'ipv6_port': res[3],
                    'name': res[4],
                    'registration_date': time.localtime(res[5]),
                    }
    except Exception as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def remove(uuid):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(uuid, UUID), "uuid is not a uuid.UUID object instance"

    try:
        database_connector = GetConnector()
        with closing(database_connector.cursor()) as db_cursor:
            db_cursor.execute("DELETE FROM controllers "
                              "WHERE controllers.uuid == ?", (uuid.bytes,))
            database_connector.commit()
            assert not GetConnector().in_transaction, "database with active transaction"
            if db_cursor.rowcount == 0:
                raise ControllerNotRegistered()
    except Exception as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def is_registered(uuid):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(uuid, UUID), "uuid is not a uuid.UUID object instance"

    try:
        with closing(GetConnector().cursor()) as db_cursor:
            db_cursor.execute("SELECT count(*) FROM controllers "
                              "WHERE controllers.uuid == ?", (uuid.bytes,))
            res = db_cursor.fetchone()
            return res[0] == 1
    except sqlite3.Error as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise Exception(str(ex))
    except Exception as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def update_addresses(uuid, ipv4_info=None, ipv6_info=None):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(uuid, UUID), "uuid is not a uuid.UUID object instance"
    assert not ((ipv4_info is None) and (ipv6_info is None)), "ipv4_info and ipv6_info cannot be null at the same time"
    assert is_ipv4_port_tuple(ipv4_info) or ipv4_info is None, "ipv4_info is invalid"
    assert is_ipv6_port_tuple(ipv6_info) or ipv6_info is None, "ipv6_info is invalid"

    try:
        database_connector = GetConnector()
        with closing(database_connector.cursor()) as db_cursor:
            db_cursor.execute("SELECT count(*) FROM controllers "
                              "WHERE controllers.uuid == ?", (uuid.bytes,))
            res = db_cursor.fetchone()
            if res[0] == 1:
                assert not GetConnector().in_transaction, "database with active transaction"
                raise ControllerAlreadyRegistered()

            if ipv4_info:
                db_cursor.execute("UPDATE controllers_ipv4s SET address=?, port=? "
                                  "WHERE id = ("
                                  "SELECT ipv4_id FROM controllers WHERE controllers.uuid = ?);",
                                  (int(ipv4_info[0]), ipv4_info[1], uuid.bytes))

            if ipv6_info:
                db_cursor.execute("UPDATE controllers_ipv6s SET address=?, port=? "
                                  "WHERE id = ("
                                  "SELECT ipv6_id FROM controllers WHERE controllers.uuid = ?);",
                                  (int(ipv6_info[0]), ipv6_info[1], uuid.bytes))
            database_connector.commit()
            assert not GetConnector().in_transaction, "database with active transaction"

    except sqlite3.Error as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise Exception(str(ex))
    except Exception as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex


def clean_slate(uuid):
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    assert isinstance(uuid, UUID), "uuid is not a uuid.UUID object instance"


    try:
        database_connector = GetConnector()
        with closing(database_connector.cursor()) as db_cursor:
            db_cursor.execute("SELECT count(*) FROM controllers "
                              "WHERE controllers.uuid == ?", (uuid.bytes,))
            res = db_cursor.fetchone()
            if res[0] == 0:
                raise ControllerNotRegistered()

            db_cursor.execute("DELETE FROM clients "
                              "WHERE controller = ("
                              "SELECT id FROM controllers WHERE controllers.uuid = ?);",
                              (uuid.bytes,))
            database_connector.commit()
    except sqlite3.Error as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise Exception(str(ex))
    except Exception as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex
