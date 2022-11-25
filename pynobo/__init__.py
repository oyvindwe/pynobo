import asyncio
import collections
from contextlib import suppress
import datetime
import errno
import logging
import time
import warnings
import socket

from pynobo import api
from pynobo.discovery import DiscoveryProtocol

_LOGGER = logging.getLogger(__name__)

# In case any of these errors occurs after successful initial connection, we will try to reconnect.
RECONNECT_ERRORS = [
    errno.ECONNRESET,   # Happens after 24 hours
    errno.ECONNREFUSED, # Not experienced, but may happen in case a reboot of the hub
    errno.EHOSTUNREACH, # May happen if hub or network switch is temporarily down
    errno.EHOSTDOWN,    # May happen if hub is temporarily down
    errno.ENETDOWN,     # May happen if local network is temporarily down
    errno.ENETUNREACH,  # May happen if hub or local network is temporarily down
    errno.ETIMEDOUT,    # Happens if hub has not responded to handshake in 60 seconds, e.g. due to network issue
]

class nobo:
    """This is where all the Nobø Hub magic happens!"""

    def __init__(self, serial, ip=None, discover=True):
        """
        Initialize logger and dictionaries.

        :param serial: The last 3 digits of the Ecohub serial number or the complete 12 digit serial number
        :param ip: IP address to search for Ecohub at (default None)
        :param discover: True/false for using UDP autodiscovery for the IP (default True)
        """

        self.serial = serial
        self.ip = ip
        self.discover = discover

        self._callbacks = []
        self._reader = None
        self._writer = None
        self._keep_alive_task = None
        self._socket_receive_task = None

        self._received_all_info = False
        self.hub_info = {}
        self.zones = collections.OrderedDict()
        self.components = collections.OrderedDict()
        self.week_profiles = collections.OrderedDict()
        self.overrides = collections.OrderedDict()
        self.temperatures = collections.OrderedDict()

    def register_callback(self, callback=lambda *args, **kwargs: None):
        """
        Register a callback to notify updates to the hub state. The callback MUST be safe to call
        from the event loop. The nobo instance is passed to the callback function. Limit callbacks
        to read state.

        :param callback: a callback method
        """
        self._callbacks.append(callback)

    def deregister_callback(self, callback=lambda *args, **kwargs: None):
        """
        Deregister a previously registered callback.

        :param callback: a callback method
        """
        self._callbacks.remove(callback)

    async def connect(self):
        """Connect to Ecohub, either by scanning or directly."""
        connected = False
        if self.discover:
            _LOGGER.info('Looking for Nobø Ecohub with serial: %s and ip: %s', self.serial, self.ip)
            discovered_hubs = await self.async_discover_hubs(serial=self.serial, ip=self.ip)
            if not discovered_hubs:
                _LOGGER.error('Failed to discover any Nobø Ecohubs')
                raise Exception('Failed to discover any Nobø Ecohubs')
            while discovered_hubs:
                (discover_ip, discover_serial) = discovered_hubs.pop()
                connected = await self.async_connect_hub(discover_ip, discover_serial)
                if connected:
                    break  # We connect to the first valid hub, no reason to try the rest
        else:
            # check if we have an IP
            if not self.ip:
                _LOGGER.error('Could not connect, no ip address provided')
                raise ValueError('Could not connect, no ip address provided')

            # check if we have a valid serial before we start connection
            if len(self.serial) != 12:
                _LOGGER.error('Could not connect, no valid serial number provided')
                raise ValueError('Could not connect, no valid serial number provided')

            connected = await self.async_connect_hub(self.ip, self.serial)

        if not connected:
            _LOGGER.error('Could not connect to Nobø Ecohub')
            raise Exception(f'Failed to connect to Nobø Ecohub with serial: {self.serial} and ip: {self.ip}')

    async def start(self):
        """Discover Ecohub and start the TCP client."""

        if not self._writer:
            await self.connect()

        # Start the tasks to send keep-alive and receive data
        self._keep_alive_task = asyncio.create_task(self.keep_alive())
        self._socket_receive_task = asyncio.create_task(self.socket_receive())
        _LOGGER.info('connected to Nobø Ecohub')

    async def stop(self):
        """Stop the keep-alive and receiver tasks and close the connection to Nobø Ecohub."""
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._keep_alive_task
        if self._socket_receive_task:
            self._socket_receive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._keep_alive_task
        await self.close()
        _LOGGER.info('disconnected from Nobø Ecohub')

    async def close(self):
        """Close the connection to Nobø Ecohub."""
        if self._writer:
            self._writer.close()
            with suppress(ConnectionError):
                await self._writer.wait_closed()
            self._writer = None
            _LOGGER.info('connection closed')

    async def async_connect_hub(self, ip, serial):
        """
        Attempt initial connection and handshake.

        :param ip: The ecohub ip address to connect to
        :param serial: The complete 12 digit serial number of the hub to connect to
        """

        self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(ip, 27779), timeout=5)

        # start handshake: "HELLO <version of command set> <Hub s.no.> <date and time in format 'yyyyMMddHHmmss'>\r"
        await self.async_send_command([api.START, api.VERSION, serial, time.strftime('%Y%m%d%H%M%S')])

        # receive the response data (4096 is recommended buffer size)
        response = await asyncio.wait_for(self.get_response(), timeout=5)
        _LOGGER.debug('first handshake response: %s', response)

        # successful response is "HELLO <its version of command set>\r"
        if response[0] == api.START:
            # send “REJECT\r” if command set is not supported? No need to abort if Hub is ok with the mismatch?
            if response[1] != api.VERSION:
                #await self.async_send_command([nobo.API.REJECT])
                _LOGGER.warning('api version might not match, hub: v%s, pynobo: v%s', response[1], api.VERSION)
                warnings.warn(f'api version might not match, hub: v{response[1]}, pynobo: v{api.VERSION}') #overkill?

            # send/receive handshake complete
            await self.async_send_command([api.HANDSHAKE])
            response = await asyncio.wait_for(self.get_response(), timeout=5)
            _LOGGER.debug('second handshake response: %s', response)

            if response[0] == api.HANDSHAKE:
                # Connect OK, store full serial for reconnect
                self.hub_ip = ip
                self.hub_serial = serial

                # Get initial data
                await asyncio.wait_for(self._get_initial_data(), timeout=5)
                for callback in self._callbacks:
                    callback(self)
                return True
            else:
                # Something went wrong...
                _LOGGER.error('Final handshake not as expected %s', response)
                await self.close()
                raise Exception(f'Final handshake not as expected {response}')
        if response[0] == api.REJECT:
            # This may not be the hub we are looking for

            # Reject response: "REJECT <reject code>\r"
            # 0=Client command set version too old (or too new!).
            # 1=Hub serial number mismatch.
            # 2=Wrong number of arguments.
            # 3=Timestamp incorrectly formatted
            _LOGGER.warning('connection to hub rejected: %s', response)
            await self.close()
            return False

        # Unexpected response
        _LOGGER.error('connection to hub rejected: %s', response)
        raise Exception(f'connection to hub rejected: {response}')

    async def reconnect_hub(self):
        """Attempt to reconnect to the hub."""

        _LOGGER.info('reconnecting to hub')
        # Pause keep alive during reconnect
        self._keep_alive = False
        # TODO: set timeout?
        if self.discover:
            # Reconnect using complete serial, but allow ip to change unless originally provided
            discovered_hubs = await self.async_discover_hubs(ip=self.ip, serial=self.hub_serial, rediscover=True)
            while discovered_hubs:
                (discover_ip, discover_serial) = discovered_hubs.pop()
                try:
                    connected = await self.async_connect_hub(discover_ip, discover_serial)
                    if connected:
                        break
                except OSError as e:
                    # We know we should be able to connect, because we just discovered the IP address. However, if
                    # the connection was lost due to network problems on our host, we must wait until we have a local
                    # IP address. E.g. discovery may find Nobø Ecohub before DHCP address is assigned.
                    if e.errno in RECONNECT_ERRORS:
                        _LOGGER.warning("Failed to connect to ip %s: %s", discover_ip, e)
                        discovered_hubs.add( (discover_ip, discover_serial) )
                        await asyncio.sleep(1)
                    else:
                        raise e
        else:
            connected = False
            while not connected:
                _LOGGER.debug('Discovery disabled - waiting 10 seconds before trying to reconnect.')
                await asyncio.sleep(10)
                with suppress(asyncio.TimeoutError):
                    try:
                        connected = await self.async_connect_hub(self.ip, self.serial)
                    except OSError as e:
                        if e.errno in RECONNECT_ERRORS:
                            _LOGGER.debug('Ignoring %s', e)
                        else:
                            raise e

        self._keep_alive = True
        _LOGGER.info('reconnected to Nobø Hub')

    @staticmethod
    def discover_hubs(serial="", ip=None, autodiscover_wait=3.0, loop=None):
        if loop is not None:
            _LOGGER.warning("loop is deprecated")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(nobo.async_discover_hubs(serial, ip, autodiscover_wait))

    @staticmethod
    async def async_discover_hubs(serial="", ip=None, autodiscover_wait=3.0, loop=None, rediscover=False):
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
        :param loop: deprecated
        :param rediscover: if true, run until the hub is discovered

        :return: a set of hubs matching that serial, ip address or both
        """

        if loop is not None:
            _LOGGER.warning("loop is deprecated.")
        transport, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: DiscoveryProtocol(serial, ip),
            local_addr=('0.0.0.0', 10000),
            reuse_port=nobo._reuse_port())
        try:
            await asyncio.sleep(autodiscover_wait)
            while rediscover and not protocol.hubs:
                await asyncio.sleep(autodiscover_wait)
        finally:
            transport.close()
        return protocol.hubs

    @staticmethod
    def _reuse_port() -> bool:
        """
        Check if we can set `reuse_port` when listening for broadcasts. To support Windows.
        """
        if hasattr(socket, 'SO_REUSEPORT'):
            sock = socket.socket(type=socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                sock.close()
                return True
            except OSError:
                pass
        return False

    async def keep_alive(self, interval = 14):
        """
        Send a periodic handshake. Needs to be sent every < 30 sec, preferably every 14 seconds.

        :param interval: seconds between each handshake. Default 14.
        """
        self._keep_alive = True
        while True:
            await asyncio.sleep(interval)
            if self._keep_alive:
                await self.async_send_command([api.HANDSHAKE])

    async def async_send_command(self, commands):
        """
        Send a list of command string(s) to the hub.

        :param commands: list of commands, either strings or integers
        """
        if not self._writer:
            return

        _LOGGER.debug('sending: %s', commands)

        # Convert integers to string
        for idx, c in enumerate(commands):
            if isinstance(c, int):
                commands[idx] = str(c)

        message = ' '.join(commands).encode('utf-8')
        try:
            self._writer.write(message + b'\r')
            await self._writer.drain()
        except ConnectionError as e:
            _LOGGER.info('lost connection to hub (%s)', e)
            await self.close()

    async def _get_initial_data(self):
        self._received_all_info = False
        await self.async_send_command([api.GET_ALL_INFO])
        while not self._received_all_info:
            self.response_handler(await self.get_response())

    async def get_response(self):
        """
        Get a response string from the hub and reformat string list before returning it.

        :return: a single response as a list of strings where each string is a field
        """
        try:
            message = await self._reader.readuntil(b'\r')
            message = message[:-1]
        except ConnectionError as e:
            _LOGGER.info('lost connection to hub (%s)', e)
            await self.close()
            raise e
        response  = message.decode('utf-8').split(' ')
        _LOGGER.debug('received: %s', response)
        return response

    async def socket_receive(self):
        try:
            while True:
                try:
                    response = await self.get_response()
                    if response[0] == api.HANDSHAKE:
                        pass # Handshake, no action needed
                    elif response[0] == 'E':
                        _LOGGER.error('error! what did you do? %s', response)
                        # TODO: Raise something here?
                    else:
                        self.response_handler(response)
                        for callback in self._callbacks:
                            callback(self)
                except (asyncio.IncompleteReadError) as e:
                    _LOGGER.info('Reconnecting due to %s', e)
                    await self.reconnect_hub()
                except (OSError) as e:
                    if e.errno in RECONNECT_ERRORS:
                        _LOGGER.info('Reconnecting due to %s', e)
                        await self.reconnect_hub()
                    else:
                        raise e
        except asyncio.CancelledError:
            _LOGGER.debug('socket_receive stopped')
        except Exception as e:
            # Ops, now we have real problems
            _LOGGER.error('Unhandled exception %s', e, exc_info=1)
            # Just disconnect (instead of risking an infinite reconnect loop)
            await self.stop()

    def response_handler(self, response):
        """
        Handle the response(s) from the hub and update the dictionaries accordingly.

        :param response: list of strings where each string is a field
        """

        # All info incoming, clear existing info
        if response[0] == api.RESPONSE_SENDING_ALL_INFO:
            self._received_all_info = False
            self.hub_info = {}
            self.zones = {}
            self.components = {}
            self.week_profiles = {}
            self.overrides = {}

        # The added/updated info messages
        elif response[0] in [api.RESPONSE_ZONE_INFO, api.RESPONSE_ADD_ZONE , api.RESPONSE_UPDATE_ZONE]:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_ZONE, response[1:]))
            self.zones[dicti['zone_id']] = dicti
            _LOGGER.info('added/updated zone: %s', dicti['name'])

        elif response[0] in [api.RESPONSE_COMPONENT_INFO, api.RESPONSE_ADD_COMPONENT , api.RESPONSE_UPDATE_COMPONENT]:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_COMPONENT, response[1:]))
            if dicti['zone_id'] == '-1' and dicti['tempsensor_for_zone_id'] != '-1':
                dicti['zone_id'] = dicti['tempsensor_for_zone_id']
            serial = dicti['serial']
            model_id = serial[:3]
            if model_id in nobo.MODELS:
                dicti['model'] = nobo.MODELS[model_id]
            else:
                dicti['model'] = nobo.model(
                    model_id,
                    nobo.model.UNKNOWN,
                    f'Unknown (serial number: {serial[:3]} {serial[3:6]} {serial[6:9]} {serial[9:]})'
                )
            self.components[dicti['serial']] = dicti
            _LOGGER.info('added/updated component: %s', dicti['name'])

        elif response[0] in [api.RESPONSE_WEEK_PROFILE_INFO, api.RESPONSE_ADD_WEEK_PROFILE, api.RESPONSE_UPDATE_WEEK_PROFILE]:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_WEEK_PROFILE, response[1:]))
            dicti['profile'] = response[-1].split(',')
            self.week_profiles[dicti['week_profile_id']] = dicti
            _LOGGER.info('added/updated week profile: %s', dicti['name'])

        elif response[0] in [api.RESPONSE_OVERRIDE_INFO, api.RESPONSE_ADD_OVERRIDE]:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_OVERRIDE, response[1:]))
            self.overrides[dicti['override_id']] = dicti
            _LOGGER.info('added/updated override: id %s', dicti['override_id'])

        elif response[0] in [api.RESPONSE_HUB_INFO, api.RESPONSE_UPDATE_HUB_INFO]:
            self.hub_info = collections.OrderedDict(zip(api.STRUCT_KEYS_HUB, response[1:]))
            _LOGGER.info('updated hub info: %s', self.hub_info)
            if response[0] == api.RESPONSE_HUB_INFO:
                self._received_all_info = True

        # The removed info messages
        elif response[0] == api.RESPONSE_REMOVE_ZONE:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_ZONE, response[1:]))
            self.zones.pop(dicti['zone_id'], None)
            _LOGGER.info('removed zone: %s', dicti['name'])

        elif response[0] == api.RESPONSE_REMOVE_COMPONENT:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_COMPONENT, response[1:]))
            self.components.pop(dicti['serial'], None)
            _LOGGER.info('removed component: %s', dicti['name'])

        elif response[0] == api.RESPONSE_REMOVE_WEEK_PROFILE:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_WEEK_PROFILE, response[1:]))
            self.week_profiles.pop(dicti['week_profile_id'], None)
            _LOGGER.info('removed week profile: %s', dicti['name'])

        elif response[0] == api.RESPONSE_REMOVE_OVERRIDE:
            dicti = collections.OrderedDict(zip(api.STRUCT_KEYS_OVERRIDE, response[1:]))
            self.overrides.pop(dicti['override_id'], None)
            _LOGGER.info('removed override: %s', dicti['override_id'])

        # Component temperature data
        elif response[0] == api.RESPONSE_COMPONENT_TEMP:
            self.temperatures[response[1]] = response[2]
            _LOGGER.info('updated temperature from %s: %s', response[1], response[2])

        # Internet settings
        elif response[0] == api.RESPONSE_UPDATE_INTERNET_ACCESS:
            internet_access = response[1]
            encryption_key = 0
            for i in range(2, 18):
                encryption_key = (encryption_key << 8) + int(response[i])
            _LOGGER.info('internet enabled: %s, key: %s', internet_access, hex(encryption_key))

        else:
            _LOGGER.warning('behavior undefined for this response: %s', response)
            warnings.warn(f'behavior undefined for this response: {response}') #overkill?

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
        command = [api.ADD_OVERRIDE, '1', mode, type, end_time, start_time, target_type, target_id]
        await self.async_send_command(command)
        for o in self.overrides: # Save override before command has finished executing
            if self.overrides[o]['target_id'] == target_id:
                self.overrides[o]['mode'] = mode
                self.overrides[o]['type'] = type

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
        command = [api.UPDATE_ZONE] + list(self.zones[zone_id].values())

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
        _LOGGER.debug('Status at %s on weekday %s is %s', target, dt.weekday(), api.DICT_WEEK_PROFILE_STATUS_TO_NAME[status])
        return api.DICT_WEEK_PROFILE_STATUS_TO_NAME[status]

    def get_zone_override_mode(self, zone_id):
        """
        Get the override mode of a zone.

        :param zone_id: the zone id in question

        :return: the override mode for the zone
        """
        mode = api.NAME_NORMAL
        for o in self.overrides:
            if self.overrides[o]['mode'] == '0':
                continue # "normal" overrides
            elif (self.overrides[o]['target_type'] == api.OVERRIDE_TARGET_ZONE
                  and self.overrides[o]['target_id'] == zone_id):
                mode = api.DICT_OVERRIDE_MODE_TO_NAME[self.overrides[o]['mode']]
                # Takes precedence over global override
                break
            elif (self.zones[zone_id]['override_allowed'] == '1'
                  and self.overrides[o]['target_type'] == api.OVERRIDE_TARGET_GLOBAL):
                mode = api.DICT_OVERRIDE_MODE_TO_NAME[self.overrides[o]['mode']]

        _LOGGER.debug('Current override for zone %s is %s', self.zones[zone_id]['name'], mode)
        return mode

    def get_current_zone_mode(self, zone_id, now=datetime.datetime.today()):
        """
        Get the mode of a zone at a certain time. If the zone is overridden only now is possible.

        :param zone_id: the zone id in question
        :param now: datetime for the status in question (default datetime.datetime.today())

        :return: the mode for the zone
        """
        current_time = (now.hour*100) + now.minute
        current_mode = self.get_zone_override_mode(zone_id)
        if current_mode == api.NAME_NORMAL:
            # no override - find mode from week profile
            current_mode = self.get_week_profile_status(self.zones[zone_id]['week_profile_id'], now)

        _LOGGER.debug('Current mode for zone %s at %s is %s', self.zones[zone_id]['name'], current_time, current_mode)
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
            _LOGGER.debug('Current temperature for component %s is %s', self.components[serial]['name'], current_temperature)
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
            _LOGGER.debug('Current temperature for zone %s is %s', self.zones[zone_id]['name'], current_temperature)
        return current_temperature
