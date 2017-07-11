"""Interfaces, constants, property names, etc. for peak.net"""

from protocols import Interface, Attribute, declareImplementation
from peak.util.imports import whenImported

__all__ = [
    'IClientSocketAddr', 'IClientSocket',
    'IListenSocketAddr', 'IListeningSocket',
    'IConnectionFactory', 'IBaseConnection', 'IRWConnection',
    'IReadConnection', 'IWriteConnection', 
]


class IClientSocket(Interface):
    """XXX See python socket module for methods of a socket"""


class IListeningSocket(Interface):
    """XXX See python socket module for methods of a socket
    Note that this socket has been listen()'d"""


whenImported(
    # If sockets are used, declare that they implement the socket interfaces
    'socket',
    lambda socket:
        declareImplementation(
            socket.socket,
            instancesProvide=[IClientSocket,IListeningSocket]
        )
)










class IConnectionFactory(Interface):
    """Thing that can create connections or listen for them"""

    def connect(timeout=None,attempts=1,delay=1,exponent=2,random=0.1):
        """Yield outgoing 'IRWConnection' objects (XXX timeouts,retries)"""

    def listen(queuesize=5):
        """Yield incoming 'IRWConnection' objects"""


class IBaseConnection(Interface):
    """Closable pipe/socket connection

    XXX Introspection needed?  getpeername?  isOpen?
    """
    
    def close():
        """Close the connection"""


class IReadConnection(IBaseConnection):
    """Readable pipe/socket"""

    def read(nbytes):
        """Yield 'nbytes' bytes from connection, or less if EOF"""

    def readline(maxlen=None, delimiter='\n'):
        """Yield one line from connection of up to 'maxlen' bytes"""


class IWriteConnection(IBaseConnection):

    """Writable pipe/socket"""

    def write(data):
        """Yield once 'data' has been buffered or written to the connection"""


class IRWConnection(IReadConnection,IWriteConnection):
    """Two-way connection"""

class IClientSocketAddr(Interface):
    """An address that can specify a client socket connection"""

    def connect_addrs(self):
        """return a list of tuples, a'la socket.getaddrinfo(), that
        the caller may attempt to create sockets with and connect on"""


class IListenSocketAddr(Interface):
    """An address that can specify sockets to listen on"""

    def listen_addrs(self):
        """return a list of tuples, a'la socket.getaddrinfo(), that
        the caller may attempt to create listening sockets on"""



























