import asyncio
import logging


_LOGGER = logging.getLogger(__name__)

class DiscoveryProtocol(asyncio.DatagramProtocol):
    """Protocol to discover Nobø Echohub on local network."""

    def __init__(self, serial = '', ip = None):
        """
        :param serial: The last 3 digits of the Ecohub serial number or the complete 12 digit serial number
        :param ip: ip address to search for Ecohub at (default None)
        """
        self.serial = serial
        self.ip = ip
        self.hubs = set()

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        msg = data.decode('utf-8')
        _LOGGER.info('broadcast received: %s from %s', msg, addr[0])
        # Expected string “__NOBOHUB__123123123”, where 123123123 is replaced with the first 9 digits of the Hub’s serial number.
        if msg.startswith('__NOBOHUB__'):
            discover_serial = msg[11:]
            discover_ip = addr[0]
            if len(self.serial) == 12:
                if discover_serial != self.serial[0:9]:
                    # This is not the Ecohub you are looking for
                    discover_serial = None
                else:
                    discover_serial = self.serial
            else:
                discover_serial += self.serial
            if self.ip and discover_ip != self.ip:
                # This is not the Ecohub you are looking for
                discover_ip = None
            if discover_ip and discover_serial:
                self.hubs.add( (discover_ip, discover_serial) )
