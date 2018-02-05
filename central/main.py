#!/usr/bin/env python3
# coding=utf-8

"""
Central Management for Openflow Networks

Developed for the SelfNet and Mobiwise research projects at Instituto de Telecomunicações, Aveiro, Portugal

This program is part of the ArchSDN system, which is composed of a Central management controller program, and a Sector
management controller program.
"""

import asyncio
import logging
import sys
from arg_parsing import parse_arguments
import signal
import functools

from helpers import custom_logging_callback, logger_module_name

import zmq_requests


# Initialize Exception Hook
sys.excepthook = (lambda tp, val, tb: custom_logging_callback(logging.getLogger(), logging.ERROR, tp, val, tb))


# Initialize logger for this module
__log_format = '[{asctime:^s}][{levelname:^8s}][{name:s}|{funcName:s}|{lineno:d}]: {message:s}'
__log_datefmt = '%Y/%m/%d|%H:%M:%S.%f (%Z)'
__log = logging.getLogger(logger_module_name(__file__))


def quit_callback(signame):
    __log.warning('Got signal {:s}: exit'.format(signame))
    asyncio.get_event_loop().stop()


if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()

        # registering callbacks to answer SIGINT and SIGTERM signals
        for signame in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(getattr(signal, signame), functools.partial(quit_callback, signame))

        parsed_args = parse_arguments()
        if sys.flags.debug:
            logging.basicConfig(format=__log_format, datefmt=__log_datefmt, style='{', level=logging.DEBUG)
        else:
            logging.basicConfig(format=__log_format, datefmt=__log_datefmt, style='{', level=parsed_args.logLevel)

        __log.info(
            ''.join(['CLI arguments: ']+list(
                            ('  {:s}: {:s}'.format(str(key), str(data)) for (key, data) in vars(parsed_args).items())
                        )
                    )
        )

        zmq_requests.zmq_context_initialize(parsed_args.ip, parsed_args.port)

        loop.run_forever()
        zmq_requests.zmq_context_close()

    except Exception:
        custom_logging_callback(__log, logging.ERROR, *sys.exc_info())
    finally:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    __log.warning("Central Manager is shutting down...")
    exit(0)



