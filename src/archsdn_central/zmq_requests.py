# coding=utf-8

import sys
import logging
import asyncio
import zmq
from zmq.asyncio import Context
import blosc
import pickle
from ipaddress import IPv4Address, IPv6Address

from archsdn_central import database

from archsdn_central.helpers import logger_module_name, custom_logging_callback

from archsdn_central.zmq_messages import BaseMessage, \
    RPLGenericError, RPLSuccess, \
    REQLocalTime, RPLLocalTime, \
    REQCentralNetworkPolicies, RPLCentralNetworkPolicies, \
    REQRegisterController, REQQueryControllerInfo, RPLControllerInformation, REQUnregisterController, \
    REQUpdateControllerInfo, REQUnregisterAllClients, \
    RPLControllerNotRegistered, RPLControllerAlreadyRegistered, REQIsControllerRegistered, \
    REQRegisterControllerClient, REQRemoveControllerClient, REQIsClientAssociated, \
    RPLClientNotRegistered, RPLClientAlreadyRegistered, \
    RPLIPv4InfoAlreadyRegistered, RPLIPv6InfoAlreadyRegistered, \
    RPLAfirmative, RPLNegative


# Tell asyncio to use zmq's eventloop (necessary if pyzmq is < than 17)
if zmq.pyzmq_version_info()[0] < 17:
    zmq.asyncio.install()

__context = None
__log = logging.getLogger(logger_module_name(__file__))
__loop = asyncio.get_event_loop()


def zmq_context_initialize(ip, port):
    global __context
    assert isinstance(ip, (IPv4Address, IPv6Address)), \
        "ip is not a valid IPv4Address or IPv6Address object. Got instead {:s}".format(repr(ip))
    assert isinstance(port, int), \
        "port is not a valid int object. Got instead {:s}".format(repr(port))
    assert 0 < port < 0xFFFF, \
        "port range invalid. Should be between 0 and 0xFFFF. Got {:d}".format(port)

    loop = asyncio.get_event_loop()
    __context = Context()

    async def recv_and_process():
        socket = __context.socket(zmq.REP)
        socket.bind("tcp://{:s}:{:d}".format(str(ip), port))

        while True:
            try:
                msg = pickle.loads(blosc.decompress(await socket.recv(), as_bytearray=True))
                __log.debug("Message received: {:s}".format(str(msg)))
                if isinstance(msg, BaseMessage):
                    reply = await __process_request(msg)
                    await socket.send(blosc.compress(pickle.dumps(reply)))
                else:
                    error_str = "Invalid message received: {:s}. Closing socket...".format(repr(msg))
                    __log.error(error_str)
                    await socket.send(blosc.compress(pickle.dumps(RPLGenericError(error_str))))
                    break

            except Exception as ex:
                await socket.send(blosc.compress(pickle.dumps(RPLGenericError(str(ex)))))

        __log.warning("ZMQ context is shutting down...")
    loop.create_task(recv_and_process())


def zmq_context_close():
    __context.destroy()


async def __process_request(request):
    try:
        return await _requests[type(request)](request)

    except KeyError:
        return RPLGenericError("Unknown Request: {}".format(repr(request)))

    except database.IPv4InfoAlreadyRegistered:
        return RPLIPv4InfoAlreadyRegistered()

    except database.IPv6InfoAlreadyRegistered:
        return RPLIPv6InfoAlreadyRegistered()

    except database.ControllerAlreadyRegistered:
        return RPLControllerAlreadyRegistered()

    except database.ControllerNotRegistered:
        return RPLControllerNotRegistered()

    except database.ClientAlreadyRegistered:
        return RPLClientAlreadyRegistered()

    except database.ClientNotRegistered:
        return RPLClientNotRegistered()

    except Exception as ex:
        custom_logging_callback(__log, logging.ERROR, *sys.exc_info())
        if sys.flags.debug:
            return RPLGenericError(str(ex))
        return RPLGenericError("Internal Error. Cannot process request.")


async def __req_local_time(request):
    return RPLLocalTime()


async def __req_central_network_policies(request):
    database_info = await database.info()
    return RPLCentralNetworkPolicies(**database_info)


async def __req_register_controller(request):
    await database.register_controller(
        uuid=request.controller_id,
        ipv4_info=request.ipv4_info,
        ipv6_info=request.ipv6_info
    )
    return RPLSuccess()


async def __req_query_controller_info(request):
    controller_info = await database.query_controller_info(request.controller_id)
    return RPLControllerInformation(**controller_info)


async def __req_update_controller_info(request):
    await database.update_controller_addresses(request.controller_id, request.ipv4_info, request.ipv6_info)
    return RPLSuccess()


async def __req_unregister_controller(request):
    await database.remove_controller(request.controller_id)
    return RPLSuccess()


async def __req_is_controller_registered(request):
    if await database.is_controller_registered(request.controller_id):
        return RPLAfirmative()
    return RPLNegative()


async def __req_register_controller_client(request):
    await database.register_client(request.client_id, request.controller_id)
    return RPLSuccess()


async def __req_remove_controller_client(request):
    await database.remove_client(request.client_id, request.controller_id)
    return RPLSuccess()


async def __req_is_client_associated(request):
    if await database.is_client_registered(request.client_id, request.controller_id):
        return RPLAfirmative()
    return RPLNegative()


async def __req_unregister_all_clients(request):
    await database.remove_all_clients(request.controller_id)
    return RPLSuccess()


_requests = {
    REQLocalTime: __req_local_time,
    REQCentralNetworkPolicies: __req_central_network_policies,
    REQRegisterController: __req_register_controller,
    REQQueryControllerInfo: __req_query_controller_info,
    REQUnregisterController: __req_unregister_controller,
    REQIsControllerRegistered: __req_is_controller_registered,
    REQRegisterControllerClient: __req_register_controller_client,
    REQRemoveControllerClient: __req_remove_controller_client,
    REQIsClientAssociated: __req_is_client_associated,
    REQUpdateControllerInfo: __req_update_controller_info,
    REQUnregisterAllClients: __req_unregister_all_clients
}
