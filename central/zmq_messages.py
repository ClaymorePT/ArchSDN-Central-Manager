# coding=utf-8

import logging
from abc import ABC, abstractmethod
from uuid import UUID
from netaddr import EUI
from ipaddress import IPv4Address, IPv6Address, ip_network
import time
from helpers import logger_module_name

__log = logging.getLogger(logger_module_name(__file__))


########################
## Abstract Messages ###
########################


class BaseMessage(ABC):
    '''
        Abstract Base Message for all message types
    '''
    _version = 1

    @abstractmethod
    def __getstate__(self):
        pass

    @abstractmethod
    def __setstate__(self, d):
        pass

    # def __repr__(self):
    #     return "{:s} at address 0x{:X}".format(
    #         str(self.__class__), id(self)
    #     )

    def __str__(self):
        return "{:s}: {:s}".format(
            str(self.__class__),
            "; ".join(list(("{}: {}".format(key, self.__dict__[key]) for key in self.__dict__)))
        )


class BaseError(BaseMessage, BaseException):
    '''
        Abstract Base Message for Errors
    '''
    pass


class RequestMessage(BaseMessage):
    '''
        Abstract Base Message for Requests
    '''
    pass


class ReplyMessage(BaseMessage):
    '''
        Abstract Base Message for Replies
    '''
    pass

########################
###  Error Messages  ###
########################


class RPL_Error(BaseError):

    def __init__(self, reason):
        self.__reason = reason

    def __getstate__(self):
        return self.__reason

    def __setstate__(self, state):
        self.__reason = state

    def __str__(self):
        return "{:s}: {:s}".format(str(self.__class__), self.__reason)


########################
### Request Messages ###
########################

class REQ_WithoutState(RequestMessage):
    '''
        Message used by controllers to request the local time.
    '''
    def __getstate__(self):
        return False

    def __setstate__(self, s):
        pass


class REQ_LocalTime(REQ_WithoutState):
    '''
        Message used by controllers to request the local time.
    '''
    pass


class REQ_CentralNetworkPolicies(REQ_WithoutState):
    '''
        Message used by controllers to request the network configurations
    '''
    pass


class REQ_Register_Controller(RequestMessage):
    '''
        Message used by controllers to register themselves at the central manager.
        Attributes:
            - Controller ID - UUID
            - Controller IPv4 Info Tuple
              - IPv4
              - Port
            - Controller IPv6 Info Tuple
              - IPv6
              - Port
    '''

    def __init__(self, controller_id, ipv4_info=None, ipv6_info=None):
        assert isinstance(controller_id, UUID), "uuid is not a uuid.UUID object instance"
#        assert not ((ipv4_info is None) and (
#                    ipv6_info is None)), "ipv4_info and ipv6_info cannot be null at the same time"
#        assert ipv4_info(ipv4_info) or ipv4_info is None, "ipv4_info is invalid"
#        assert ipv6_info(ipv6_info) or ipv6_info is None, "ipv6_info is invalid"

        self.controller_id = controller_id
        self.ipv4_info = ipv4_info
        self.ipv6_info = ipv6_info

    def __getstate__(self):
        return (
            self.controller_id.bytes,
            (self.ipv4_info[0].packed, self.ipv4_info[1]) if self.ipv4_info != None else None,
            (self.ipv6_info[0].packed, self.ipv6_info[1]) if self.ipv6_info != None else None
        )

    def __setstate__(self, state):
        self.controller_id = UUID(bytes=state[0])
        self.ipv4_info = (IPv4Address(state[1][0]), state[1][1]) if state[1] != None else None
        self.ipv6_info = (IPv6Address(state[2][0]), state[2][1]) if state[2] != None else None


class REQ_Query_Controller_Info(RequestMessage):
    '''
        Message used to request the detailed information about a controller.
        Attributes:
            - Controller ID - UUID
    '''
    def __init__(self, controller_id):
        assert isinstance(controller_id, UUID), "uuid is not a uuid.UUID object instance"

        self.controller_id = controller_id

    def __getstate__(self):
        return self.controller_id.bytes

    def __setstate__(self, state):
        self.controller_id = UUID(bytes=state)

#
# class REQ_Unregister_Controller(BaseMessage):
#     '''
#         Message used Unregister a Controller.
#         Attributes:
#             - Controller ID - UUID
#     '''
#
#     def __init__(self):
#         pass
#
#
# class REQ_Is_Controller_Registered(BaseMessage):
#     '''
#         Message used to check if a Controller is Registered.
#         Attributes:
#             - Controller ID - UUID
#     '''
#
#     def __init__(self):
#         pass
#
#
# class REQ_Update_Controller_Info(BaseMessage):
#     '''
#         Message used by controllers to register themselves at the central manager.
#         Attributes:
#             - Controller ID - UUID
#             - Controller IPv4 Info Tuple
#               - IPv4
#               - Port
#             - Controller IPv6 Info Tuple
#               - IPv6
#               - Port
#
#     '''
#     def __init__(self):
#         pass
#
#
# class REQ_Register_Controller_Client(BaseMessage):
#     '''
#         Message used to Register a Client.
#         Attributes:
#             - Controller ID - UUID
#             - Client ID
#     '''
#     def __init__(self):
#         pass
#
#
#
# class REQ_Remove_Controller_Client(BaseMessage):
#     '''
#         Message used to Remove a Client Registration.
#         Attributes:
#             - Controller ID - UUID
#             - Client ID
#     '''
#     def __init__(self):
#         pass
#
#
# class REQ_Is_Client_Associated(BaseMessage):
#     '''
#         Message used to query if a specific Client Registration exists.
#         Attributes:
#             - Controller ID - UUID
#             - Client ID
#     '''
#
#     def __init__(self):
#         pass



########################
###  Reply Messages  ###
########################

class RPL_WithoutState(ReplyMessage):
    '''
        Base Message for Replies with no state
    '''
    def __getstate__(self):
        return False

    def __setstate__(self, s):
        pass


class RPL_Success(RPL_WithoutState):
    '''
        Message used by controllers to register themselves at the central manager.
        Attributes:
            - Controller ID - UUID
            - Controller IPv4 Info Tuple
              - IPv4
              - Port
            - Controller IPv6 Info Tuple
              - IPv6
              - Port
    '''
    pass


class RPL_LocalTime(ReplyMessage):
    '''
        Message used by the central to reply the local time.
    '''
    def __init__(self):
        self.__time = time.time()

    def __getstate__(self):
        return self.__time

    def __setstate__(self, state):
        self.__time = state


class RPL_CentralNetworkPolicies(ReplyMessage):
    '''
        Message used by central manager to reply with the network configurations
    '''

    def __init__(self, ipv4_network, ipv6_network, ipv4_service, ipv6_service, mac_service, registration_date):
        self.ipv4_network = ipv4_network
        self.ipv6_network = ipv6_network
        self.ipv4_service = ipv4_service
        self.ipv6_service = ipv6_service
        self.mac_service = mac_service
        self.registration_date = registration_date

    def __getstate__(self):
        return (
            self.ipv4_network.network_address.packed, int(self.ipv4_network.prefixlen),
            self.ipv6_network.network_address.packed, int(self.ipv6_network.prefixlen),
            self.ipv4_service.packed,
            self.ipv6_service.packed,
            int(self.mac_service),
            self.registration_date
        )

    def __setstate__(self, state):
        self.ipv4_network = ip_network((state[0], state[1]))
        self.ipv6_network = ip_network((state[2], state[3]))
        self.ipv4_service = IPv4Address(state[4])
        self.ipv6_service = IPv6Address(state[5])
        self.mac_service = EUI(state[6])
        self.registration_date = state[7]


class RPL_ControllerInformation(ReplyMessage):
    '''
        Message used by central manager to reply with the controller information
    '''

    def __init__(self, ipv4, ipv4_port, ipv6, ipv6_port, name, registration_date):
        self.ipv4 = ipv4
        self.ipv4_port = ipv4_port
        self.ipv6 = ipv6
        self.ipv6_port = ipv6_port
        self.name = name
        self.registration_date = registration_date

    def __getstate__(self):
        return (
            self.ipv4.packed, self.ipv4_port,
            self.ipv6.packed, self.ipv6_port,
            self.name.encode('ascii'),
            self.registration_date
        )

    def __setstate__(self, state):
        self.ipv4 = IPv4Address(state[0])
        self.ipv4_port = state[1]
        self.ipv6 = IPv6Address(state[2])
        self.ipv6_port = state[3]
        self.name = state[4].decode('ascii')
        self.registration_date = state[5]


###########################
## Subscription Messages ##
###########################



