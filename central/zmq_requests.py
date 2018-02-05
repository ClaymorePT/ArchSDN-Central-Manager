# coding=utf-8

import sys
import logging
import asyncio
import zmq
from zmq.asyncio import Context, Poller
import blosc

from helpers import logger_module_name, custom_logging_callback

# Tell asyncio to use zmq's eventloop (necessary if pyzmq is < than 17)
if zmq.pyzmq_version_info()[0] < 17:
    zmq.asyncio.install()

__context = None
__log = logging.getLogger(logger_module_name(__file__))

def zmq_context_initialize(ipv4, port):
    global __context
    loop = asyncio.get_event_loop()
    __context = Context()


    async def recv_and_process():
        socket = __context.socket(zmq.REP)
        socket.bind("tcp://{:s}:{:d}".format(ipv4, port))

        while (True):
            try:
                msg = await socket.recv_multipart()  # waits for msg to be ready
                __log.debug("{}".format(str(msg)))
                await socket.send_multipart(msg)

            except Exception:
                custom_logging_callback(__log, logging.ERROR, *sys.exc_info())

    loop.create_task(recv_and_process())


def zmq_context_close():
    __context.destroy()




def __send_message(socket, obj, flags=0):
    return socket.send(blosc.compress(bytes(obj)), flags=flags)

def __recv_message(socket, flags=0):
    compressed_obj_bytes = socket.recv(flags)
    return blosc.decompress(compressed_obj_bytes)

def __process_request(request):
    pass




# async def Ping(data=None):
#     __log.info("Client {}:{} requested a ping with data:\n {}".format(ip, port, data))
#     return (UUID(int=4), EUI(1))