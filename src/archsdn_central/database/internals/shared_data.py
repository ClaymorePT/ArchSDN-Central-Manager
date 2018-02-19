# This is just a module to keep a reference to the database connector.
# This is necessary because the Python multiprocessing module is not capable of serializing sqlite3 database connectors.
#
__database_connector = None


def GetConnector():
    return __database_connector


def SetConnector(conn):
    global __database_connector
    __database_connector = conn