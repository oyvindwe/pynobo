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
UPDATE_HUB_INFO = 'U03'         # Updates hub information: U83 <Snr> <Name> <DefaultAwayOverrideLength> <ActiveOverrideid> <Softwareversion> <Hardwareversion> <ProductionDate>
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
RESPONSE_HUB_INFO = 'H05'           # G00 request complete signal + static info: H05 <Snr> <Name> <DefaultAwayOverrideLength> <ActiveOverrideid> <SoftwareVersion> <HardwareVersion> <ProductionDate>

EXECUTE_START_SEARCH = 'X00'
EXECUTE_STOP_SEARCH = 'X01'
EXECUTE_COMPONENT_PAIR = 'X03'
RESPONSE_STARTED_SEARCH = 'Y00'
RESPONSE_STOPPED_SEARCH = 'Y01'
RESPONSE_COMPONENT_TEMP = 'Y02'     # Component temperature value sent as part of a GOO response, or pushed from the Hub automatically to all connected clients whenever the Hub has received updated temperature data.
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
