

class ControllerNotRegistered(Exception):
    def __str__(self):
        return "Controller not registered"


class ControllerAlreadyRegistered(Exception):
    def __str__(self):
        return "Controller already registered"


class ClientNotRegistered(Exception):
    def __str__(self):
        return "Client not registered"


class ClientAlreadyRegistered(Exception):
    def __str__(self):
        return "Client already registered"


class NoResultsAvailable(Exception):
    def __str__(self):
        return "No Results Avaliable"


class IPv4InfoAlreadyRegistered(Exception):
    def __str__(self):
        return "IPv4 Info already registered"


class IPv6InfoAlreadyRegistered(Exception):
    def __str__(self):
        return "IPv6 Info already registered"


class NameAlreadyRegistered(Exception):
    def __str__(self):
        return "Name already registered"


