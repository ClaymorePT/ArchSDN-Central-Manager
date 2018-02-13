import pathlib
import argparse
import ipaddress

def validate_path(location):
    if location == ":memory:":
        return location
    loc = pathlib.Path(location)
    loc_parent = loc.parent
    if not loc_parent.exists():
        raise argparse.ArgumentTypeError("Location {:s} does not exist.".format(str(loc_parent)))
    return(loc)


def validate_address(address):
    try:
        ip = ipaddress.ip_address(address)
        if not ip.is_multicast and not ip.is_unspecified:
            return ip
        else:
            raise argparse.ArgumentTypeError("Invalid IP address: {:s}".format(address))
    except Exception:
        raise argparse.ArgumentTypeError("Invalid IP address: {:s}".format(address))

def validate_ipv4network(address):
    try:
        ip = ipaddress.IPv4Network(address)
        if ip.is_private:
            return ip
        else:
            raise argparse.ArgumentTypeError("Invalid IPv4 network address: {:s}".format(address))
    except Exception:
        raise argparse.ArgumentTypeError("Invalid IPv4 network address: {:s}".format(address))

def validate_ipv6network(address):
    try:
        ip = ipaddress.IPv6Network(address)
        if ip.is_private:
            return ip
        else:
            raise argparse.ArgumentTypeError("Invalid IPv6 network address: {:s}".format(address))
    except Exception:
        raise argparse.ArgumentTypeError("Invalid IPv6 network address: {:s}".format(address))

def validate_port(port):
    try:
        p = int(port)
        if p in range(1024, 0xFFFF):
            return p
        else:
            raise argparse.ArgumentTypeError("Invalid Port: {:s}".format(port))
    except Exception:
        raise argparse.ArgumentTypeError("Invalid Port: {:s}".format(port))


def parse_arguments():

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logLevel", help="Logging Level (default: %(default)s)", type=str,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO")
    parser.add_argument("-i", "--ip", help="Central Server interface IP to bind (default: %(default)s)",
                        type=validate_address, default="127.0.0.1")
    parser.add_argument("-p", "--port", help="Central Server Port (default: %(default)s)", type=int, default=12345)
    parser.add_argument("-s", "--storage", help="SQLite3 Database Location (default: ./%(default)s)",
                        type=validate_path, default=':memory:')
    parser.add_argument("-4net", "--ipv4network", help="IPv4 Network for Hosts (default: ./%(default)s)",
                        type=validate_ipv4network, default="10.0.0.0/8")
    parser.add_argument("-6net", "--ipv6network",
                        help="IPv6 Network for Hosts (default (archsdn in hex): ./%(default)s)",
                        type=validate_ipv6network,
                        default="fd61:7263:6873:646e::0/64")  # 61:7263:6873:646e -> archsdn in hex

    return parser.parse_args()