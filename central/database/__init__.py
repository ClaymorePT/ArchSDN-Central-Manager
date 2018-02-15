__all__ = ["initialise",
           "info",
           "close",
           "register_controller",
           "query_controller_info",
           "remove_controller",
           "is_controller_registered",
           "update_controller_addresses",
           "remove_all_clients",
           "register_client",
           "query_client_info",
           "remove_client",
           "is_client_registered",
           "ControllerNotRegistered",
           "ControllerAlreadyRegistered",
           "ClientNotRegistered",
           "ClientAlreadyRegistered",
           "IPv4InfoAlreadyRegistered",
           "IPv6InfoAlreadyRegistered",
           "NoResultsAvailable",
           ]


import asyncio
from threading import Thread, Event
import sys
import atexit
import logging
from helpers import logger_module_name, custom_logging_callback

from .internals.exceptions import \
    ControllerNotRegistered as __ControllerNotRegistered, \
    ControllerAlreadyRegistered as __ControllerAlreadyRegistered, \
    ClientNotRegistered as __ClientNotRegistered, \
    ClientAlreadyRegistered as __ClientAlreadyRegistered, \
    IPv4InfoAlreadyRegistered as __IPv4InfoAlreadyRegistered, \
    IPv6InfoAlreadyRegistered as __IPv6InfoAlreadyRegistered,  \
    NoResultsAvailable as __NoResultsAvailable

from .internals import \
    init_database as __initialise, \
    info as __info, \
    close_database as __close, \
    register_controller as __register_controller, \
    controller_infos as __query_controller_info, \
    remove_controller as __remove_controller, \
    is_controller_registered as __is_controller_registered, \
    update_controller_addresses as __update_controller_addresses, \
    remove_all_clients as __remove_all_clients, \
    register_client as __register_client, \
    client_info as __query_client_info, \
    remove_client as __remove_client, \
    is_client_registered as __is_client_registered

__log = logging.getLogger(logger_module_name(__file__))


_callbacks = {
    "initialise": __initialise,
    "info": __info,
    "close": __close,
    "register_controller": __register_controller,
    "query_controller_info": __query_controller_info,
    "remove_controller": __remove_controller,
    "is_controller_registered": __is_controller_registered,
    "update_controller_addresses": __update_controller_addresses,
    "remove_all_clients": __remove_all_clients,
    "register_client": __register_client,
    "query_client_info": __query_client_info,
    "remove_client": __remove_client,
    "is_client_registered": __is_client_registered
}

_exceptions = {
    "ControllerNotRegistered": __ControllerNotRegistered,
    "ControllerAlreadyRegistered": __ControllerAlreadyRegistered,
    "ClientNotRegistered": __ClientNotRegistered,
    "ClientAlreadyRegistered": __ClientAlreadyRegistered,
    "IPv4InfoAlreadyRegistered": __IPv4InfoAlreadyRegistered,
    "IPv6InfoAlreadyRegistered": __IPv6InfoAlreadyRegistered,
    "NoResultsAvailable": __NoResultsAvailable
}


class __Wrapper:
    def __init__(self, wrapped):
        self.__wrapped = wrapped
        self.__thread_loop = asyncio.new_event_loop()
        self.__shutdown_event = Event()
        boot_event = Event()

        if sys.flags.debug:
            self.__thread_loop.set_debug(True)

        def database_thread_main(event_loop):
            try:
                async def unlock_wrapper():
                    boot_event.set()

                asyncio.set_event_loop(event_loop)
                asyncio.run_coroutine_threadsafe(unlock_wrapper(), event_loop)
                event_loop.run_forever()
            except Exception as ex:
                print(ex)
            finally:
                self.__shutdown_event.set()

        self.__database_thread = Thread(target=database_thread_main, args=(self.__thread_loop,), daemon=True)
        self.__database_thread.start()
        boot_event.wait()

    def __getattr__(self, name):
        if name in _exceptions:
            return _exceptions[name]

        if (name != 'shutdown') and (name not in _callbacks):
            raise AttributeError("module has no member called {:s}".format(name))

        if name is 'shutdown':
            def attr():
                self.__thread_loop.call_soon_threadsafe(self.__thread_loop.stop)
                self.__shutdown_event.wait()
                self.__thread_loop.call_soon_threadsafe(self.__thread_loop.close)
            return attr

        def attr(*args, **kwargs):
            async def cr(*args, **kwargs):
                return _callbacks[name](*args, **kwargs)

            return asyncio.wrap_future(asyncio.run_coroutine_threadsafe(cr(*args, **kwargs), self.__thread_loop))

        return attr


sys.modules[__name__] = __Wrapper(sys.modules[__name__])
atexit.register(sys.modules[__name__].shutdown)
