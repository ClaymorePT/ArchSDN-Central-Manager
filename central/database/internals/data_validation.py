from ipaddress import IPv4Address, IPv6Address


def is_ipv4_port_tuple(ipv4_info):
    return type(ipv4_info) is tuple and \
           len(ipv4_info) == 2 and \
           type(ipv4_info[0]) is IPv4Address and \
           type(ipv4_info[1]) is int and \
           0 < ipv4_info[1] <= 0xFFFF


def is_ipv6_port_tuple(ipv6_info):
    return type(ipv6_info) is tuple and \
           len(ipv6_info) == 2 and \
           type(ipv6_info[0]) is IPv6Address and \
           type(ipv6_info[1]) is int and \
           0 < ipv6_info[1] <= 0xFFFF
