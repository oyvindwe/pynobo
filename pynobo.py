#!/usr/bin/python3

import asyncio
import collections
from contextlib import suppress
import datetime
import logging
import time
import threading
import warnings

_LOGGER = logging.getLogger(__name__)

class nobo:
    """This is where all the Nobø Hub magic happens!"""

    class API:
        """
        All the commands and responses from API v1.1.
        Some with sensible names, others not yet given better names.
        """

        VERSION = '1.1'

        START = 'HELLO'             #HELLO <version of command set> <Hub s.no.> <date and time in format 'yyyyMMddHHmmss'>
        REJECT = 'REJECT'           #REJECT <reject code>
        HANDSHAKE = 'HANDSHAKE'     #HANDSHAKE

        ADD_ZONE = 'A00'            # Adds Zone to hub database: A00 <Zone id> <Name> <Active week profile id> <Comfort temperature> <Eco temperature> <Allow overrides> <Active override id>
        ADD_COMPONENT = 'A01'       # Adds Component to hub database: A01 <Serial  number>  <Status> <Name> <Reverse on/off?> <Zoneld> <Active override Id> <Temperature sensor for zone>
        ADD_WEEK_PROFILE = 'A02'    # Adds Week Profile to hub database: A02 <Week profile id> <Name> <Profile>
        ADD_OVERRIDE = 'A03'        # Adds an override to hub database: A03 <Id> <Mode> <Type> <End time> <Start time> <Override target> <Override target ID>
        RESPONSE_ADD_ZONE = 'B00'
        RESPONSE_ADD_COMPONENT = 'B01'
        RESPONSE_ADD_WEEK_PROFILE = 'B02'
        RESPONSE_ADD_OVERRIDE = 'B03'

        UPDATE_ZONE = 'U00'             # Updates Zone to hub database: U00 <Zone id> <Name> <Active week profile id> <Comfort temperature> <Eco temperature> <Allow overrides> <Active override id>
        UPDATE_COMPONENT = 'U01'        # Updates Component to hub database: U01 <Serial number> <Status> <Name> <Reverse on/off?> <Zoneld> <Active override Id> <Temperature sensor for zone>
        UPDATE_WEEK_PROFILE = 'U02'     # Updates Week Profile to hub database: U02 <Week profile id> <Name> <Profile>
        UPDATE_HUB_INFO = 'U03'         # Updates hub information: U83 <Snr> <Name> <DefaultAwayOverrideLength> <ActiveOverrideid> <Softwareversion> <Hardwareversion> <Producti????
        UPDATE_INTERNET_ACCESS = 'U06'  # Updates hub internet connectivity function and encryption key (LAN only): U86 <Enable internet access> <Encryption key> <Reserved 1> <Reserved 2>
        RESPONSE_UPDATE_ZONE = 'V00'
        RESPONSE_UPDATE_COMPONENT = 'V01'
        RESPONSE_UPDATE_WEEK_PROFILE = 'V02'
        RESPONSE_UPDATE_HUB_INFO = 'V03'
        RESPONSE_UPDATE_INTERNET_ACCESS = 'V06'

        # Removes a Zone from the hub's internal database. All values except Zone lD is ignored.
        # Any Components in the Zone are also deleted (and S02 Component deleted messages arc sent for the deleted Components).
        # Any Component used as temperature sensor for the Zone is modified to no longer be temperature sensor for the Zone (and a V0l Component updated message is sent).
        # R00 <Zone id> <Name> <Active week profile id> <Comfort temperature> <Eco temperature> <Allow overrides> <Active override id>
        REMOVE_ZONE = 'R00'

        # Removes a Component from the hub's internal database. All values except Component Serial Number is ignored.
        # R01 <Serial number> <Status> <Name> <Reverse on/off?> <Zoneid> <Active override Id> <Temperature sensor for zone>
        REMOVE_COMPONENT = 'R01'

        # Removes a WeekProfile from the hub's intemal  database. All values except  Week Profile lD is ignored.
        # Any Zones that are set to use the Week Profile are set to use the default Week Profile in stead (and V00 Zone updated messages are sent).
        # R02 <Week profile id> <Name> <Profile>
        REMOVE_WEEK_PROFILE = 'R02'

        RESPONSE_REMOVE_ZONE = 'S00'
        RESPONSE_REMOVE_COMPONENT = 'S01'
        RESPONSE_REMOVE_WEEK_PROFILE = 'S02'
        RESPONSE_REMOVE_OVERRIDE = 'S03'

        # Gets all information from hub. Will trigger a sequence  of series of one HOO message, zero or more
        # HOI, zero or more H02, zero or more Y02, zero or more H03, zero or more H04 commands, one V06
        # message if <.:onne<.:ted v ia LAN (not Internet), and lastly a H05 message. 'll1e client  knows
        # that the Hub is tlnished  sending all info when it has received  the H05 mess3ge.
        GET_ALL_INFO = 'G00'

        # (Never  used by the Nobo Energy  Control app- you should only use GOO.) Gets all Zones lrom hub.
        # Will trigger a series of H01 messages from the Hub.
        GET_ALL_ZONES = 'G01'

        # (Never  used by the Nobo Energy  Control app - you should only use GOO.) Gets all Components li·om hub.
        # Will result i n a series of H02 messages  from the Hub.
        GET_ALL_COMPONENTS = 'G02'

        # (Never used by the Nobo Energy Control app- you should only use GOO.) Gets all WeekProfile data from hub.
        # Will trigger a series of 1103 messages from the lluh.
        GET_ALL_WEEK_PROFILES = 'G03'

        # (Never used by the Nobo Energy Control app - you should only use GOO.) Gets all active overrrides from hub.
        # Will trigger a series of H04 messages from the Hub.
        GET_ACTIVE_OVERRIDES = 'G04'

        RESPONSE_SENDING_ALL_INFO = 'H00'   # Response to GET_ALL_INFO signifying that all relevant info stored in Hub is about to be sent.
        RESPONSE_ZONE_INFO = 'H01'          # Response with Zone info, one per message: H01 <Zone id> <Name> <Active week profile id> <Comfort temperature> <Eco temperature> <Allow overrides> <Active override id>
        RESPONSE_COMPONENT_INFO = 'H02'     # Response with Component info, one per message: H02 <Serial number> <Status> <Name> <Reverse on/off?> <Zoneld> <Active override Id> <Temperature sensor for zone>
        RESPONSE_WEEK_PROFILE_INFO = 'H03'  # Response with Week Profile info, one per message: H03 <Week profile id> <Name> <Profile>
        RESPONSE_OVERRIDE_INFO = 'H04'      # Response with override info, one per message: H04 <Id> <Mode> <Type> <End time> <Start time> <Override target> <Override target ID>
        RESPONSE_HUB_INFO = 'H05'           # G00 request complete signal + static info: H05 <Snr> <Name> <DefaultAwayOverrideLength> <ActiveOverrideid> <SoftwareVersion> <HardwareVersion> <Producti???

        EXECUTE_START_SEARCH = 'X00'
        EXECUTE_STOP_SEARCH = 'X01'
        EXECUTE_COMPONENT_PAIR = 'X03'
        RESPONSE_STARTED_SEARCH = 'Y00'
        RESPONSE_STOPPED_SEARCH = 'Y01'
        RESPONSE_COMPONENT_TEMP = 'Y02'     # Component temperature value sent as part ora GOO response, or pushed from the Hub a utomaticall y to all connected clients whenever the Hub has received updated temperature data.
        RESPONSE_COMPONENT_PAIR = 'Y03'
        RESPONSE_COMPONENT_FOUND = 'Y04'

        RESPONSE_ERROR = 'E00'              # Other error messages than E00 may also be sent from the Hub (E01, E02 etc.): E00 <command> <message>

        OVERRIDE_MODE_NORMAL = '0'
        OVERRIDE_MODE_COMFORT = '1'
        OVERRIDE_MODE_ECO = '2'
        OVERRIDE_MODE_AWAY = '3'

        OVERRIDE_TYPE_NOW = '0'
        OVERRIDE_TYPE_TIMER = '1'
        OVERRIDE_TYPE_FROM_TO = '2'
        OVERRIDE_TYPE_CONSTANT = '3'

        OVERRIDE_TARGET_GLOBAL = '0'
        OVERRIDE_TARGET_ZONE = '1'
        OVERRIDE_TARGET_COMPONENT = '2'     # Not implemented yet

        OVERRIDE_ID_NONE = '-1'
        OVERRIDE_ID_HUB = '-1'

        WEEK_PROFILE_STATE_ECO = '0'
        WEEK_PROFILE_STATE_COMFORT = '1'
        WEEK_PROFILE_STATE_AWAY = '2'
        WEEK_PROFILE_STATE_OFF = '4'

        STRUCT_KEYS_HUB = ['serial', 'name', 'default_away_override_length', 'override_id', 'software_version', 'hardware_version', 'production_date']
        STRUCT_KEYS_ZONE = ['zone_id', 'name', 'week_profile_id', 'temp_comfort_c', 'temp_eco_c', 'override_allowed', 'deprecated_override_id']
        STRUCT_KEYS_COMPONENT = ['serial', 'status', 'name', 'reverse_onoff', 'zone_id', 'override_id', 'tempsensor_for_zone_id']
        STRUCT_KEYS_WEEK_PROFILE = ['week_profile_id', 'name', 'profile'] # profile is minimum 7 and probably more values separated by comma
        STRUCT_KEYS_OVERRIDE = ['override_id', 'mode', 'type', 'end_time', 'start_time', 'target_type', 'target_id']

        NAME_OFF = 'off'
        NAME_AWAY = 'away'
        NAME_ECO = 'eco'
        NAME_COMFORT = 'comfort'
        NAME_NORMAL = 'normal'

        DICT_OVERRIDE_MODE_TO_NAME = {OVERRIDE_MODE_NORMAL : NAME_NORMAL, OVERRIDE_MODE_COMFORT : NAME_COMFORT, OVERRIDE_MODE_ECO : NAME_ECO, OVERRIDE_MODE_AWAY : NAME_AWAY}
        DICT_WEEK_PROFILE_STATUS_TO_NAME = {WEEK_PROFILE_STATE_ECO : NAME_ECO, WEEK_PROFILE_STATE_COMFORT : NAME_COMFORT, WEEK_PROFILE_STATE_AWAY : NAME_AWAY, WEEK_PROFILE_STATE_OFF : NAME_OFF}
        DICT_NAME_TO_OVERRIDE_MODE = {NAME_NORMAL : OVERRIDE_MODE_NORMAL, NAME_COMFORT : OVERRIDE_MODE_COMFORT, NAME_ECO : OVERRIDE_MODE_ECO, NAME_AWAY : OVERRIDE_MODE_AWAY}
        DICT_NAME_TO_WEEK_PROFILE_STATUS = {NAME_ECO : WEEK_PROFILE_STATE_ECO, NAME_COMFORT : WEEK_PROFILE_STATE_COMFORT, NAME_AWAY : WEEK_PROFILE_STATE_AWAY, NAME_OFF : WEEK_PROFILE_STATE_OFF}

    class DiscoveryProtocol(asyncio.DatagramProtocol):
        """Protocol to discover Nobø Echohub on local network."""

        def __init__(self, serial = "", ip = None):
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
            msg = data.decode("utf-8")
            _LOGGER.info('broadcast received: %s', msg)
            # Expected string “__NOBOHUB__123123123”, where 123123123 is replaced with the first 9 digits of the Hub’s serial number.
            if msg.startswith("__NOBOHUB__"):
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

    def __init__(self, serial, ip=None, discover=True, loop: asyncio.AbstractEventLoop = None):
        """
        Initialize logger and dictionaries.

        :param serial: The last 3 digits of the Ecohub serial number or the complete 12 digit serial number
        :param ip: ip address to search for Ecohub at (default None)
        :param discover: True/false for using UDP autodiscovery for the IP (default True)
        :param loop: the asyncio event loop to use
        """

        self._loop = asyncio.get_event_loop() if loop is None else loop
        self.serial = serial
        self.ip = ip
        self.discover = discover

        self.callbacks = []
        self.reader = None
        self.writer = None

        self.received_all_info = False
        self.hub_info = {}
        self.zones = collections.OrderedDict()
        self.components = collections.OrderedDict()
        self.week_profiles = collections.OrderedDict()
        self.overrides = collections.OrderedDict()
        self.temperatures = collections.OrderedDict()

        # Start asyncio in a separate thread unless an event loop was provided.
        if loop is None:
            self._loop.run_until_complete(self.start())
            self._thread = threading.Thread(target=lambda: self._loop.run_forever())
            self._thread.start()
        else:
            self._thread = None

    def register_callback(self, callback=lambda *args, **kwargs: None):
        """
        Register a callback to notify updates to the hub state. The callback MUST be safe to call
        from the event loop. The nobo instance is passed to the callback function. Limit callbacks
        to read state.

        :param callback: a callback method
        """
        self.callbacks.append(callback)

    def deregister_callback(self, callback=lambda *args, **kwargs: None):
        """
        Deregister a previously registered callback.

        :param callback: a callback method
        """
        self.callbacks.remove(callback)

    async def start(self):
        """Discover Ecohub and start the TCP client."""

        if not self.writer:
            # Get a socket connection, either by scanning or directly
            if self.discover:
                _LOGGER.info("Looking for Nobø Ecohub serial: %s, ip: %s", self.serial, self.ip)
                discovered_hubs = await self.async_discover_hubs(serial=self.serial, ip=self.ip, loop=self._loop)
                if not discovered_hubs:
                    _LOGGER.error("Failed to discover any Nobø Ecohubs")
                    raise Exception("Failed to discover any Nobø Ecohubs")
                while discovered_hubs:
                    (discover_ip, discover_serial) = discovered_hubs.pop()
                    try:
                        await self.async_connect_hub(discover_ip, discover_serial)
                        break  # We connect to the first valid hub, no reason to try the rest
                    except Exception as e:
                        # This might not have been the Ecohub we wanted (wrong serial)
                        _LOGGER.warning("Could not connect to {}:{} - {}".format(
                            discover_ip, discover_serial, e))
            else:
                # check if we have an IP
                if not self.ip:
                    _LOGGER.error('Could not connect, no ip address provided')
                    raise ValueError('Could not connect, no ip address provided')

                # check if we have a valid serial before we start connection
                if len(self.serial) != 12:
                    _LOGGER.error('Could not connect, no valid serial number provided')
                    raise ValueError('Could not connect, no valid serial number provided')

                await self.async_connect_hub(self.ip, self.serial)

            if not self.writer:
                _LOGGER.error("Failed to connect to Ecohub")
                raise Exception("Failed to connect to Ecohub")

        # Start the tasks to send keep-alive and receive data
        self.keep_alive_task = self._loop.create_task(self.keep_alive())
        self.socket_receive_task = self._loop.create_task(self.socket_receive())

        _LOGGER.info('connected to Nobø Ecohub')

    async def stop(self):
        """Stop the keep-alive and receiver tasks and close the connection to Nobø Ecohub."""
        self.keep_alive_task.cancel()
        with suppress(asyncio.CancelledError):
            await self.keep_alive_task
        self.socket_receive_task.cancel()
        with suppress(asyncio.CancelledError):
            await self.keep_alive_task
        await self.close()
        _LOGGER.info('disconnected from Nobø Ecohub')

    async def close(self):
        """Close the connection to Nobø Ecohub."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None

    def connect_hub(self, ip, serial):
        return self._loop.run_until_complete(self.async_connect_hub(ip, serial))

    async def async_connect_hub(self, ip, serial):
        """
        Attempt initial connection and handshake.

        :param ip: The ecohub ip address to connect to
        :param serial: The complete 12 digit serial number of the hub to connect to
        """

        self.reader, self.writer = await asyncio.open_connection(ip, 27779)

        # start handshake: "HELLO <version of command set> <Hub s.no.> <date and time in format 'yyyyMMddHHmmss'>\r"
        await self.async_send_command([self.API.START, self.API.VERSION, serial, time.strftime('%Y%m%d%H%M%S')])

        # receive the response data (4096 is recommended buffer size)
        response = await asyncio.wait_for(self.get_response(), timeout=5)
        _LOGGER.debug('first handshake response: %s', response)

        # successful response is "HELLO <its version of command set>\r"
        if response[0][0] == self.API.START:
            # send “REJECT\r” if command set is not supported? No need to abort if Hub is ok with the mismatch?
            if response[0][1] != self.API.VERSION:
                #await self.async_send_command([self.API.REJECT])
                _LOGGER.warning('api version might not match, hub: v{}, pynobo: v{}'.format(response[0][1], self.API.VERSION))
                warnings.warn('api version might not match, hub: v{}, pynobo: v{}'.format(response[0][1], self.API.VERSION)) #overkill?

            # send/receive handshake complete
            await self.async_send_command([self.API.HANDSHAKE])
            response = await asyncio.wait_for(self.get_response(), timeout=5)
            _LOGGER.debug('second handshake response: %s', response)

            if response[0][0] == self.API.HANDSHAKE:
                # Connect OK, store connection information for later reconnects
                self.hub_ip = ip
                self.hub_serial = serial

                # Get initial data
                # TODO: Move to separate method
                # TODO: Add timeout for getting initial data
                self.received_all_info = False
                await self.async_send_command([self.API.GET_ALL_INFO])
                while not self.received_all_info:
                    responses = await self.get_response()
                    for r in responses:
                        self.response_handler(r)
                # Initial state received - notify listeners.
                for callback in self.callbacks:
                    callback(self)
                return
            else:
                # Something went wrong...
                _LOGGER.error("Final handshake not as expected %s", response[0][0])
                await self.close()
                raise Exception("Final handshake not as expected {}".format(response[0][0]))
        else:
            # Reject response: "REJECT <reject code>\r"
            # 0=client command set version too old (or too new!).
            # 1=Hub serial number mismatch.
            # 2=Wrong number of arguments.
            # 3=Timestamp incorrectly formatted
            _LOGGER.error('connection to hub rejected: {}'.format(response[0]))
            await self.close()
            raise Exception('connection to hub rejected: {}'.format(response[0]))

    def reconnect_hub(self, ip, serial):
        self._loop.run_until_complete(self.async_reconnect_hub())

    async def async_reconnect_hub(self):
        """Attempt to disconnect/close the connection and reconnect"""
        # close socket properly so connect_hub can restart properly
        await self.close()

        # attempt reconnect to the lost hub
        rediscovered_hub = None
        while not rediscovered_hub:
            _LOGGER.debug('hub not rediscovered')
            rediscovered_hub = self.async_discover_hubs(serial=self.hub_serial, ip=self.hub_ip, loop=self._loop)
            await asyncio.sleep(10)
        await self.async_connect_hub(self.hub_ip, self.hub_serial)
        _LOGGER.info('reconnected to Nobø Hub')

    @staticmethod
    def discover_hubs(serial="", ip=None, autodiscover_wait=3.0, loop=None):
        loop = asyncio.get_event_loop() if loop is None else loop
        return loop.run_until_complete(nobo.async_discover_hubs(serial, ip, autodiscover_wait, loop))

    @staticmethod
    async def async_discover_hubs(serial="", ip=None, autodiscover_wait=3.0, loop=None):
        """
        Attempt to autodiscover Nobø Ecohubs on the local network.

        Every two seconds, the Hub sends one UDP broadcast packet on port 10000
        to broadcast IP 255.255.255.255, we listen for this package, and collect
        every packet that contains the magic __NOBOHUB__ identifier. The set
        of (ip, serial) tuples is returned.

        Specifying a complete 12 digit serial number or an ip address, will only
        attempt to discover hubs matching that serial, ip address or both.

        Specifyng the last 3 digits of the serial number will append this to the
        discovered serial number.

        Not specifying serial or ip will include all found hubs on the network,
        but only the discovered part of the serial number (first 9 digits).

        :param serial: The last 3 digits of the Ecohub serial number or the complete 12 digit serial number
        :param ip: ip address to search for Ecohub at (default None)
        :param autodiscover_wait: how long to wait for an autodiscover package from the hub (default 3.0)

        :return: a set of hubs matching that serial, ip address or both
        """

        loop = asyncio.get_event_loop() if loop is None else loop
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: nobo.DiscoveryProtocol(serial, ip),
            local_addr=('0.0.0.0', 10000),
            reuse_port=True)
        try:
            await asyncio.sleep(autodiscover_wait)
        finally:
            transport.close()
        return protocol.hubs

    async def keep_alive(self, interval = 14):
        """
        Send a periodic handshake. Needs to be sent every < 30 sec, preferably every 14 seconds.

        :param interval: seconds between each handshake. Default 14.
        """
        while True:
            await asyncio.sleep(interval)
            _LOGGER.debug("handshake")
            await self.async_send_command([self.API.HANDSHAKE])

    def send_command(self, commands):
        self._loop.create_task(self.async_send_command(commands))

    async def async_send_command(self, commands):
        """
        Send a list of command string(s) to the hub.

        :param commands: list of commands, either strings or integers
        """
        if not self.writer:
            return

        _LOGGER.debug('sending: %s', commands)

        # Convert integers to string
        for idx, c in enumerate(commands):
            if isinstance(c, int):
                commands[idx] = str(c)

        message = ' '.join(commands).encode('utf-8')
        try:
            self.writer.write(message + b'\r')
            await self.writer.drain()
        except ConnectionError as e:
            _LOGGER.info('lost connection to hub (%s)', e)
            await self.close()

    async def get_response(self, bufsize=4096):
        """
        Get a response string from the hub and reformat string list before returning it.

        :param bufsize: maximum bytes to receive from the socket  (default 4096)

        :return: a list of string responses
        """
        response = b''
        while response[-1:] != b'\r':
            try:
                response += await self.reader.read(bufsize)
            except ConnectionError as e:
                _LOGGER.info('lost connection to hub (%s)', e)
                await self.close()
                break

        # Handle more than one response in one receive
        response_list = str(response.decode("utf-8")).split('\r')
        response = []
        for r in response_list:
            if r:
                response.append(r.split(' '))

        return response

    async def socket_receive(self):
        try:
            while True:
                do_callback = False
                responses = await self.get_response()
                for r in responses:
                    _LOGGER.debug('received: %s', r)
                    if r[0] == self.API.HANDSHAKE:
                        pass # Handshake, no action needed
                    elif r[0][0] == 'E':
                        _LOGGER.error('error! what did you do? %s', r)
                        # TODO: Raise something here?
                    else:
                        self.response_handler(r)
                        do_callback = True
                # Handle all responses before callback to avoid multiple callbacks if get_response
                # returns more than one response.
                if do_callback:
                    for callback in self.callbacks:
                        callback(self)
                # TODO: Reconnect if necessary
        except Exception as e:
            # Ops, now we have real problems
            _LOGGER.error("Unhandled exception: %s", e, exc_info=1)
            # Just disconnect (in stead of risking an infinite reconnect loop)
            await self.stop()

    def response_handler(self, r):
        """
        Handle the response(s) from the hub and update the dictionaries accordingly.

        :param r: a list of string responses
        """

        # All info incoming, clear existing info
        if r[0] == self.API.RESPONSE_SENDING_ALL_INFO:
            self.received_all_info = False
            self.hub_info = {}
            self.zones = {}
            self.components = {}
            self.week_profiles = {}
            self.overrides = {}

        # The added/updated info messages
        elif r[0] in [self.API.RESPONSE_ZONE_INFO, self.API.RESPONSE_ADD_ZONE ,self.API.RESPONSE_UPDATE_ZONE]:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_ZONE, r[1:]))
            self.zones[dicti['zone_id']] = dicti
            _LOGGER.info('added/updated zone: %s', dicti['name'])

        elif r[0] in [self.API.RESPONSE_COMPONENT_INFO, self.API.RESPONSE_ADD_COMPONENT ,self.API.RESPONSE_UPDATE_COMPONENT]:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_COMPONENT, r[1:]))
            if dicti['zone_id'] == '-1' and dicti['tempsensor_for_zone_id'] != '-1':
                dicti['zone_id'] = dicti['tempsensor_for_zone_id']
            self.components[dicti['serial']] = dicti
            _LOGGER.info('added/updated component: %s', dicti['name'])

        elif r[0] in [self.API.RESPONSE_WEEK_PROFILE_INFO, self.API.RESPONSE_ADD_WEEK_PROFILE, self.API.RESPONSE_UPDATE_WEEK_PROFILE]:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_WEEK_PROFILE, r[1:]))
            dicti['profile'] = r[-1].split(',')
            self.week_profiles[dicti['week_profile_id']] = dicti
            _LOGGER.info('added/updated week profile: %s', dicti['name'])

        elif r[0] in [self.API.RESPONSE_OVERRIDE_INFO, self.API.RESPONSE_ADD_OVERRIDE]:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_OVERRIDE, r[1:]))
            self.overrides[dicti['override_id']] = dicti
            _LOGGER.info('added/updated override: id %s', dicti['override_id'])

        elif r[0] in [self.API.RESPONSE_HUB_INFO, self.API.RESPONSE_UPDATE_HUB_INFO]:
            self.hub_info = collections.OrderedDict(zip(self.API.STRUCT_KEYS_HUB, r[1:]))
            _LOGGER.info('updated hub info: %s', self.hub_info)
            if r[0] == self.API.RESPONSE_HUB_INFO:
                self.received_all_info = True

        # The removed info messages
        elif r[0] == self.API.RESPONSE_REMOVE_ZONE:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_ZONE, r[1:]))
            self.zones.pop(dicti['zone_id'], None)
            _LOGGER.info('removed zone: %s', dicti['name'])

        elif r[0] == self.API.RESPONSE_REMOVE_COMPONENT:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_COMPONENT, r[1:]))
            self.components.pop(dicti['serial'], None)
            _LOGGER.info('removed component: %s', dicti['name'])

        elif r[0] == self.API.RESPONSE_REMOVE_WEEK_PROFILE:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_WEEK_PROFILE, r[1:]))
            self.week_profiles.pop(dicti['week_profile_id'], None)
            _LOGGER.info('removed week profile: %s', dicti['name'])

        elif r[0] == self.API.RESPONSE_REMOVE_OVERRIDE:
            dicti = collections.OrderedDict(zip(self.API.STRUCT_KEYS_OVERRIDE, r[1:]))
            self.overrides.pop(dicti['override_id'], None)
            _LOGGER.info('removed override: id%s', dicti['override_id'])

        # Component temperature data
        elif r[0] == self.API.RESPONSE_COMPONENT_TEMP:
            self.temperatures[r[1]] = r[2]
            _LOGGER.info('updated temperature from {}: {}'.format(r[1], r[2]))

        # Internet settings
        elif r[0] == self.API.RESPONSE_UPDATE_INTERNET_ACCESS:
            internet_access = r[1]
            encryption_key = 0
            for i in range(2, 18):
                encryption_key = (encryption_key << 8) + int(r[i])
            _LOGGER.debug('internet enabled: {}, key: {}'.format(internet_access, hex(encryption_key)))

        else:
            _LOGGER.warning('behavior undefined for this response: {}'.format(r))
            warnings.warn('behavior undefined for this response: {}'.format(r)) #overkill?

    def create_override(self, mode, type, target_type, target_id='-1', end_time='-1', start_time='-1'):
        self._loop.create_task(self.async_create_override(mode, type, target_type, target_id, end_time, start_time))

    async def async_create_override(self, mode, type, target_type, target_id='-1', end_time='-1', start_time='-1'):
        """
        Override hub/zones/components. Use OVERRIDE_MODE_NOMAL to disable an existing override.

        :param mode: API.OVERRIDE_MODE. NORMAL, COMFORT, ECO or AWAY
        :param type: API.OVERRIDE_TYPE. NOW, TIMER, FROM_TO or CONSTANT
        :param target_type: API.OVERRIDE_TARGET. GLOBAL or ZONE
        :param target_id: the target id (default -1)
        :param end_time: the end time (default -1)
        :param start_time: the start time (default -1)
        """
        command = [self.API.ADD_OVERRIDE, '1', mode, type, end_time, start_time, target_type, target_id]
        await self.async_send_command(command)
        for o in self.overrides: # Save override before command has finished executing
            if self.overrides[o]['target_id'] == target_id:
                self.overrides[o]['mode'] = mode
                self.overrides[o]['type'] = type

    def update_zone(self, zone_id, name=None, week_profile_id=None, temp_comfort_c=None, temp_eco_c=None, override_allowed=None):
        self._loop.create_task(self.async_update_zone(zone_id, name, week_profile_id, temp_comfort_c, temp_eco_c, override_allowed))

    async def async_update_zone(self, zone_id, name=None, week_profile_id=None, temp_comfort_c=None, temp_eco_c=None, override_allowed=None):
        """
        Update the name, week profile, temperature or override allowing for a zone.

        :param zone_id: the zone id
        :param name: the new zone name (default None)
        :param week_profile_id: the new id for a week profile (default None)
        :param temp_comfort_c: the new comfort temperature (default None)
        :param temp_eco_c: the new eco temperature (default None)
        :param override_allowed: the new override allow setting (default None)
        """

        # Initialize command with the current zone settings
        command = [self.API.UPDATE_ZONE] + list(self.zones[zone_id].values())

        # Replace command with arguments that are not None. Is there a more elegant way?
        if name:
            command[2] = name
        if week_profile_id:
            command[3] = week_profile_id
        if temp_comfort_c:
            command[4] = temp_comfort_c
            self.zones[zone_id]['temp_comfort_c'] = temp_comfort_c # Save setting before sending command
        if temp_eco_c:
            command[5] = temp_eco_c
            self.zones[zone_id]['temp_eco_c'] = temp_eco_c # Save setting before sending command
        if override_allowed:
            command[6] = override_allowed

        await self.async_send_command(command)

    def get_week_profile_status(self, week_profile_id, dt=datetime.datetime.today()):
        """
        Get the status of a week profile at a certain time in the week. Monday is day 0.

        :param week_profile_id: -- the week profile id in question
        :param dt: -- datetime for the status in question (default datetime.datetime.today())

        :return: the status for the profile
        """
        profile = self.week_profiles[week_profile_id]['profile']
        target = (dt.hour*100) + dt.minute
        # profile[0] is always 0000x, so this provides the initial status
        status = profile[0][-1]
        weekday = 0
        for timestamp in profile[1:]:
            if timestamp[:4] == '0000':
                weekday += 1
            if weekday == dt.weekday():
                if int(timestamp[:4]) <= target:
                    status = timestamp[-1]
                else:
                    break
        _LOGGER.debug('Status at {} on weekday {} is {}'.format(target, dt.weekday(), self.API.DICT_WEEK_PROFILE_STATUS_TO_NAME[status]))
        return self.API.DICT_WEEK_PROFILE_STATUS_TO_NAME[status]

    def get_current_zone_mode(self, zone_id, now=datetime.datetime.today()):
        """
        Get the mode of a zone at a certain time. If the zone is overridden only now is possible.

        :param zone_id: the zone id in question
        :param dt: datetime for the status in question (default datetime.datetime.today())

        :return: the mode for the zone
        """
        current_time = (now.hour*100) + now.minute
        current_mode = ''

        # check if the zone is overridden and to which mode
        if self.zones[zone_id]['override_allowed'] == '1':
            for o in self.overrides:
                if self.overrides[o]['mode'] == '0':
                    continue # "normal" overrides
                elif self.overrides[o]['target_type'] == self.API.OVERRIDE_TARGET_ZONE:
                    if self.overrides[o]['target_id'] == zone_id:
                        current_mode = self.API.DICT_OVERRIDE_MODE_TO_NAME[self.overrides[o]['mode']]
                        break
                elif self.overrides[o]['target_type'] == self.API.OVERRIDE_TARGET_GLOBAL:
                    current_mode = self.API.DICT_OVERRIDE_MODE_TO_NAME[self.overrides[o]['mode']]

        # no override - find mode from week profile
        if not current_mode:
            current_mode = self.get_week_profile_status(self.zones[zone_id]['week_profile_id'], now)

        _LOGGER.debug('Current mode for zone {} at {} is {}'.format(self.zones[zone_id]['name'], current_time, current_mode))
        return current_mode

    def get_current_component_temperature(self, serial):
        """
        Get the current temperature from a component.

        :param serial: the serial for the component in question

        :return: the temperature for the component (default N/A)
        """
        current_temperature = None

        if serial in self.temperatures:
            current_temperature = self.temperatures[serial]
            if current_temperature == 'N/A':
                current_temperature = None

        if current_temperature:
            _LOGGER.debug('Current temperature for component {} is {}'.format(self.components[serial]['name'], current_temperature))
        return current_temperature

    # Function to get (first) temperature in a zone
    def get_current_zone_temperature(self, zone_id):
        """
        Get the current temperature from (the first component in) a zone.

        :param zone_id: the id for the zone in question

        :return: the temperature for the (first) component in the zone (default N/A)
        """
        current_temperature = None

        for c in self.components:
            if self.components[c]['zone_id'] == zone_id:
                current_temperature = self.get_current_component_temperature(c)
                if current_temperature != None:
                    break

        if current_temperature:
            _LOGGER.debug('Current temperature for zone {} is {}'.format(self.zones[zone_id]['name'], current_temperature))
        return current_temperature
