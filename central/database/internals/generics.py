import logging
import sqlite3
import pathlib
from pathlib import Path
from ipaddress import IPv4Network, IPv6Network, IPv4Address, IPv6Address
from time import localtime
from contextlib import closing
from netaddr import EUI

from helpers import logger_module_name

from .shared_data import GetConnector, SetConnector

__log = logging.getLogger(logger_module_name(__file__))


def init_database(location=":memory:", ipv4_network=None, ipv6_network=None):
    assert GetConnector() is None, "database already initialized"
    assert isinstance(location, Path) or (isinstance(location, str) and location == ":memory:"), \
        "location is not an instance of Path nor str equal to :memory:"
    assert isinstance(ipv4_network, type(None)) or isinstance(ipv4_network, IPv4Network), \
        "ipv4_network not a valid IPv4 Network Address"
    assert isinstance(ipv6_network, type(None)) or isinstance(ipv6_network, IPv6Network), \
        "ipv6_network not a valid IPv6 Network Address"
    assert isinstance(ipv4_network, type(None)) or ipv4_network.is_private, \
        "ipv4_network expected to be a private network address"
    assert isinstance(ipv6_network, type(None)) or ipv6_network.is_private, \
        "ipv6_network expected to be a private network address"

    if isinstance(location, Path):
        location = str(location.absolute())

    if not ipv4_network:
        ipv4_network = IPv4Network(("10.0.0.0", 8))
    if not ipv6_network:
        ipv6_network = IPv6Network("fd61:7263:6873:646e::0/64")  # 61:7263:6873:646e -> archsdn in hex

    database_connector = sqlite3.connect(location, isolation_level='IMMEDIATE')
    SetConnector(database_connector)
    database_connector.enable_load_extension(True)
    db_sql_location = pathlib.Path(str(pathlib.Path(__file__).parents[1])+"/database.sql")
    db_cursor = database_connector.cursor()
    db_cursor.execute("SELECT count(*) FROM sqlite_master WHERE type == 'table' AND name == 'configurations';")
    res = db_cursor.fetchone()[0]
    if res == 0:
        __log.info("Database does not exist. Creating...")
        with open(db_sql_location, "r") as fp:
            database_connector.executescript("".join(fp.readlines()))

        ipv4_address = ipv4_network.network_address + 1  # +1 -> The first ipv4 network address
        db_cursor.execute("INSERT INTO clients_ipv4s(id, address) VALUES (1,?)", (int(ipv4_address),))
        ipv6_address = ipv6_network.network_address + 1  # +1 -> The first ipv6 network address
        db_cursor.execute("INSERT INTO clients_ipv6s(id, address) VALUES (1,?)", (ipv6_address.packed,))

        database_connector.execute(
            "INSERT INTO configurations(ipv4_network, ipv6_network, ipv4_service, ipv6_service, mac_service) "
            "VALUES (?,?,1,1,?);", (
                str(ipv4_network),
                str(ipv6_network),
                str(EUI("FE:FF:FF:FF:FF:FF"))
            )
        )
        database_connector.commit()
    else:
        __log.info("Database exists! Using it...")

    db_cursor = database_connector.cursor()
    db_cursor.execute("SELECT (creation_date) FROM configurations;")
    creation_date = db_cursor.fetchone()[0]
    __log.debug("Central Database initialised on the {:s}, located in {:s}, "
               "using ipv4 network {:s}, ipv6 network {:s}, "
               "service ipv4 {:s}, service ipv6 {:s}, service mac {:s}.".format(
            str(creation_date), str(location),
            str(ipv4_network), str(ipv6_network),
            str(ipv4_address),str(ipv6_address),
            str(EUI("FE:FF:FF:FF:FF:FF"))
        )
    )


def close_database():
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"

    __log.debug("Closing Database...")
    database_connector = GetConnector()
    database_connector.commit()
    database_connector.close()
    SetConnector(None)
    __log.debug("Database Closed.")


def info():
    assert GetConnector(), "database not initialized"
    assert not GetConnector().in_transaction, "database with active transaction"
    try:
        with closing(GetConnector().cursor()) as db_cursor:
            db_cursor.execute("SELECT ipv4_network, ipv6_network, "
                              "clients_ipv4s.address AS ipv4_service, clients_ipv6s.address AS ipv6_service, "
                              "mac_service, "
                              "creation_date "
                              "FROM configurations, clients_ipv4s, clients_ipv6s "
                              "WHERE (configurations.ipv4_service == clients_ipv4s.id) AND "
                              "(configurations.ipv6_service == clients_ipv6s.id)")
            res = db_cursor.fetchone()
            return {
                "ipv4_network": IPv4Network(res[0]),
                "ipv6_network": IPv6Network(res[1]),
                "ipv4_service": IPv4Address(res[2]),
                "ipv6_service": IPv6Address(res[3]),
                "mac_service": EUI(res[4]),
                "registration_date": localtime(res[5])
            }
    except sqlite3.Warning as ex:
        __log.error(str(ex))
        assert not GetConnector().in_transaction, "database with active transaction"
        raise ex
