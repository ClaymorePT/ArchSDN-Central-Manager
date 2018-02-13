# coding=utf-8

import sys
import logging
import asyncio
import zmq
from zmq.asyncio import Context
import blosc
import pickle
from ipaddress import IPv4Address, IPv6Address

from helpers import logger_module_name, custom_logging_callback

from zmq_messages import BaseMessage, \
RPL_Error, RPL_Success, \
    REQ_LocalTime, RPL_LocalTime, \
    REQ_CentralNetworkPolicies, RPL_CentralNetworkPolicies, \
    REQ_Register_Controller


# Tell asyncio to use zmq's eventloop (necessary if pyzmq is < than 17)
if zmq.pyzmq_version_info()[0] < 17:
    zmq.asyncio.install()

__context = None
__log = logging.getLogger(logger_module_name(__file__))
__loop = asyncio.get_event_loop()


def zmq_context_initialize(ip, port):
    assert isinstance(ip, (IPv4Address, IPv6Address)), \
        "ip is not a valid IPv4Address or IPv6Address object. Got instead {:s}".format(repr(ip))
    assert isinstance(port, int), \
        "port is not a valid int object. Got instead {:s}".format(repr(port))
    assert 0 < port < 0xFFFF, \
        "port range invalid. Should be between 0 and 0xFFFF. Got {:d}".format(port)


    global __context
    loop = asyncio.get_event_loop()
    __context = Context()


    async def recv_and_process():
        socket = __context.socket(zmq.REP)
        socket.bind("tcp://{:s}:{:d}".format(str(ip), port))

        while (True):
            try:
                msg = pickle.loads(blosc.decompress(await socket.recv(), as_bytearray=True))  # waits for msg to be ready
                __log.debug("Message received: {:s}".format(str(msg)))
                if isinstance(msg, BaseMessage):
                    reply = await __process_request(msg)
                    await socket.send(blosc.compress(pickle.dumps(reply)))
                else:
                    error_str = "Invalid message received: {:s}. Closing socket...".format(repr(msg))
                    __log.error(error_str)
                    await socket.send(blosc.compress(pickle.dumps(RPL_Error(error_str))))
                    break

            except Exception as ex:
                custom_logging_callback(__log, logging.ERROR, *sys.exc_info())
                await socket.send(blosc.compress(pickle.dumps(RPL_Error(str(ex)))))
        __log.warning("ZMQ context is shutting down")
    loop.create_task(recv_and_process())


def zmq_context_close():
    __context.destroy()


async def __process_request(request):
    import database


    if isinstance(request, REQ_LocalTime):
        return RPL_LocalTime()

    elif isinstance(request, REQ_CentralNetworkPolicies):
        database_info = await database.info()
        return RPL_CentralNetworkPolicies(**database_info)

    elif isinstance(request, REQ_Register_Controller):
        await database.register_controller(
            uuid=request.controller_id,
            ipv4_info=request.ipv4_info,
            ipv6_info=request.ipv6_info
        )
        return RPL_Success()
    else:
        return RPL_Error("Unknown Request: {}".format(request))

#uuid, ipv4_info=None, ipv6_info=None
#
# class ServerTask(threading.Thread):
#     """ServerTask"""
#     def __init__(self):
#         threading.Thread.__init__ (self)
#
#     def run(self):
#         context = zmq.Context()
#         frontend = context.socket(zmq.ROUTER)
#         frontend.bind('tcp://*:5570')
#
#         backend = context.socket(zmq.DEALER)
#         backend.bind('inproc://backend')
#
#         workers = []
#         for i in range(5):
#             worker = ServerWorker(context)
#             worker.start()
#             workers.append(worker)
#
#         zmq.proxy(frontend, backend)
#
#         frontend.close()
#         backend.close()
#         context.term()
#
# class ServerWorker(threading.Thread):
#     """ServerWorker"""
#     def __init__(self, context):
#         threading.Thread.__init__ (self)
#         self.context = context
#
#     def run(self):
#         worker = self.context.socket(zmq.DEALER)
#         worker.connect('inproc://backend')
#         tprint('Worker started')
#         while True:
#             ident, msg = worker.recv_multipart()
#             tprint('Worker received %s from %s' % (msg, ident))
#             replies = randint(0,4)
#             for i in range(replies):
#                 time.sleep(1. / (randint(1,10)))
#                 worker.send_multipart([ident, msg])
#
#         worker.close()
#


# async def Ping(data=None):
#     __log.info("Client {}:{} requested a ping with data:\n {}".format(ip, port, data))
#     return (UUID(int=4), EUI(1))