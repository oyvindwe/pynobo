from typing import Union


class model:
    """
    A device model that supports Nobø Ecohub.

    Official lists of devices:
    https://help.nobo.no/en/user-manual/before-you-start/what-is-a-receiver/list-of-receivers/
    https://help.nobo.no/en/user-manual/before-you-start/what-is-a-transmitter/list-of-transmitters/
    """

    THERMOSTAT_HEATER = "THERMOSTAT_HEATER"
    THERMOSTAT_FLOOR = "THERMOSTAT_FLOOR"
    THERMOSTAT_ROOM = "THERMOSTAT_ROOM"
    SWITCH = "SWITCH"
    SWITCH_OUTLET = "SWITCH_OUTLET"
    CONTROL_PANEL = "CONTROL_PANEL"
    UNKNOWN = "UNKNOWN"

    def __init__(
            self,
            model_id: str,
            type: Union[THERMOSTAT_HEATER, THERMOSTAT_FLOOR, THERMOSTAT_ROOM, SWITCH, SWITCH_OUTLET, CONTROL_PANEL, UNKNOWN],
            name: str,
            *,
            supports_comfort: bool = False,
            supports_eco: bool = False,
            requires_control_panel = False,
            has_temp_sensor: bool = False):
        self._model_id = model_id
        self._type = type
        self._name = name
        self._supports_comfort = supports_comfort
        self._supports_eco = supports_eco
        self._requires_control_panel = requires_control_panel
        self._has_temp_sensor = has_temp_sensor

    @property
    def model_id(self) -> str:
        """Model id of the component (first 3 digits of the serial number)."""
        return self._model_id

    @property
    def name(self) -> str:
        """Model name."""
        return self._name

    @property
    def type(self) -> Union[THERMOSTAT_HEATER, THERMOSTAT_FLOOR, THERMOSTAT_ROOM, SWITCH, SWITCH_OUTLET, CONTROL_PANEL, UNKNOWN]:
        """Model type."""
        return self._type

    @property
    def supports_comfort(self) -> bool:
        """Return True if comfort temperature can be set on hub."""
        return self._supports_comfort

    @property
    def supports_eco(self) -> bool:
        """Return True if eco temperature can be set on hub."""
        return self._supports_eco

    @property
    def requires_control_panel(self) -> bool:
        """Return True if setting temperature on hub requires a control panel in the zone."""
        return self._requires_control_panel

    @property
    def has_temp_sensor(self) -> bool:
        """Return True if component has a temperature sensor."""
        return self._has_temp_sensor

MODELS = {
    "120": model("120", model.SWITCH, "RS 700"),
    "121": model("121", model.SWITCH, "RSX 700"),
    "130": model("130", model.SWITCH_OUTLET, "RCE 700"),
    "160": model("160", model.THERMOSTAT_HEATER, "R80 RDC 700"),
    "165": model("165", model.THERMOSTAT_HEATER, "R80 RDC 700 LST (GB)"),
    "168": model("168", model.THERMOSTAT_HEATER, "NCU-2R", supports_comfort=True, supports_eco=True),
    "169": model("169", model.THERMOSTAT_HEATER, "DCU-2R", supports_comfort=True, supports_eco=True),
    "170": model("170", model.THERMOSTAT_HEATER, "Serie 18, ewt touch", supports_comfort=True, supports_eco=True), # Not verified if temperature can be set remotely
    "180": model("180", model.THERMOSTAT_HEATER, "2NC9 700", supports_eco=True),
    "182": model("182", model.THERMOSTAT_HEATER, "R80 RSC 700 (5-24)", supports_eco=True),
    "183": model("183", model.THERMOSTAT_HEATER, "R80 RSC 700 (5-30)", supports_eco=True),
    "184": model("184", model.THERMOSTAT_HEATER, "NCU-1R", supports_eco=True),
    "186": model("186", model.THERMOSTAT_HEATER, "DCU-1R", supports_eco=True),
    "190": model("190", model.THERMOSTAT_HEATER, "Safir", supports_comfort=True, supports_eco=True, requires_control_panel=True),
    "192": model("192", model.THERMOSTAT_HEATER, "R80 TXF 700", supports_comfort=True, supports_eco=True, requires_control_panel=True),
    "194": model("194", model.THERMOSTAT_HEATER, "R80 RXC 700", supports_comfort=True, supports_eco=True),
    "198": model("198", model.THERMOSTAT_HEATER, "NCU-ER", supports_comfort=True, supports_eco=True),
    "199": model("199", model.THERMOSTAT_HEATER, "DCU-ER", supports_comfort=True, supports_eco=True),
    "200": model("200", model.THERMOSTAT_FLOOR, "TRB 36 700"),
    "210": model("210", model.THERMOSTAT_FLOOR, "NTB-2R", supports_comfort=True, supports_eco=True),
    "220": model("220", model.THERMOSTAT_FLOOR, "TR36", supports_eco=True),
    "230": model("230", model.THERMOSTAT_ROOM, "TCU 700"),
    "231": model("231", model.THERMOSTAT_ROOM, "THB 700"),
    "232": model("232", model.THERMOSTAT_ROOM, "TXB 700"),
    "234": model("234", model.CONTROL_PANEL, "SW4", has_temp_sensor=True),
}
