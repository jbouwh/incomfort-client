"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

   Each Gateway can have up to 8 Heaters (boilers) and each Heater can have 0-2
   Room thermostats.
   """

import logging
import random
from typing import Any, Dict, List, Optional

import aiohttp

FAKE_HEATER = False
FAKE_HEATER_INDEX = 1
FAKE_HEATER_SERIAL = "9901z999999"

FAKE_ROOM = False
FAKE_ROOM_NUMBER = 2  # only 1 or 2

CLIENT_TIMEOUT = 20  # seconds

INVALID_VALUE = (2 ** 15 - 1) / 100.0  # 127 * 256 + 255 = 327.67
SERIAL_LINE = "0123456789abcdefghijklmnopqrstuvwxyz"

# key label: IO
BITMASK_BURNER = 0x08  # burner state: on / off
BITMASK_FAIL = 0x01  # failure state: on / off (aka lockout)
BITMASK_PUMP = 0x02  # pump state: on / off
BITMASK_TAP = 0x04  # tap (DHW) state: function on / off

# key label: displ_code
DISPLAY_CODES = {
    0: "opentherm",
    15: "boiler ext.",
    24: "frost",
    37: "central heating rf",
    51: "tapwater int.",
    85: "sensortest",
    102: "central heating",
    126: "standby",
    153: "postrun boiler",
    170: "service",
    204: "tapwater",
    231: "postrun ch",
    240: "boiler int.",
    255: "buffer",
}
FAULT_CODES = {
    0: "Sensor fault after self check",
    1: "Temperature too high",
    2: "S1 and S2 interchanged",
    4: "No flame signal",
    5: "Poor flame signal",
    6: "Flame detection fault",
    8: "Incorrect fan speed",
    10: "Sensor fault S1",
    11: "Sensor fault S1",
    12: "Sensor fault S1",
    13: "Sensor fault S1",
    14: "Sensor fault S1",
    20: "Sensor fault S2",
    21: "Sensor fault S2",
    22: "Sensor fault S2",
    23: "Sensor fault S2",
    24: "Sensor fault S2",
    27: "Shortcut outside sensor temperature",
    29: "Gas valve relay faulty",
    30: "Gas valve relay faulty",
}  # "0.0": "Low system pressure"

HEATER_ATTRS = [
    "display_code",
    "display_text",
    "fault_code",
    "is_burning",
    "is_failed",
    "is_pumping",
    "is_tapping",
    "heater_temp",
    "tap_temp",
    "pressure",
    "serial_no",
]
ROOM_ATTRS = ["room_temp", "setpoint", "override"]

OVERRIDE_MAX_TEMP = 30.0
OVERRIDE_MIN_TEMP = 5.0

logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s %(levelname)-8s: %(message)s",
    level=logging.WARNING,
)
_LOGGER = logging.getLogger(__name__)

# pylint: disable=protected-access, missing-docstring


def _value(key_stub: str, data_dict: dict) -> Optional[float]:
    def _convert(most_significant_byte: int, least_significant_byte: int) -> float:
        return (most_significant_byte * 256 + least_significant_byte) / 100.0

    _value = _convert(data_dict[key_stub + "_msb"], data_dict[key_stub + "_lsb"])
    return _value if _value != INVALID_VALUE else None


class InComfortObject:
    """Base for InComfortObjects."""

    def __init__(self) -> None:
        self._gateway: Gateway = None
        self._fake_room: bool = None
        self._serial_no = None  # used by heaters only

    async def _get(self, url: str):
        _LOGGER.debug(
            "_get(url=%s, auth=%s)", url, "REDACTED" if self._gateway._auth else None
        )

        if url[:17] == "data.json?heater=" and self._serial_no == FAKE_HEATER_SERIAL:
            url = "data.json?heater=0"
            _LOGGER.info("heater faked")

        async with self._gateway._session.get(
            url=f"{self._gateway._url_base}{url}",
            auth=self._gateway._auth,
            raise_for_status=True,
            timeout=self._gateway._timeout,
        ) as resp:
            response = await resp.json(content_type=None)

        # if enabled, inject a fake current temperature
        if url[:17] == "data.json?heater=" and self._fake_room:
            temp = 5 + random.randint(0, 8)
            response.update({f"room_temp_{FAKE_ROOM_NUMBER}_msb": temp})
            response.update({f"room_temp_{FAKE_ROOM_NUMBER}_lsb": 0})

            response.update({f"room_temp_set_{FAKE_ROOM_NUMBER}_msb": 7})
            response.update({f"room_temp_set_{FAKE_ROOM_NUMBER}_lsb": 158})

            _LOGGER.info(
                "room %s faked (temperature=%s, setpoint=%s)",
                _value(f"room_temp_{FAKE_ROOM_NUMBER}", response),  # 12.80-33.28C
                _value(f"room_temp_set_{FAKE_ROOM_NUMBER}", response),  # 19.50C
                FAKE_ROOM_NUMBER,
            )

        _LOGGER.debug("_get(url=%s): response = %s", url, response)
        return response


class Gateway(InComfortObject):
    """Representation of an InComfort (Lan2RF) Gateway."""

    def __init__(
        self,
        hostname: str,
        username: str = None,
        password: str = None,
        session: aiohttp.ClientSession = None,
        debug: bool = False,
    ) -> None:
        if debug is True:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is (explicitly) enabled.")

        _LOGGER.debug("Gateway(hostname=%s) instantiated.", hostname)
        super().__init__()

        self._gateway = self
        self._hostname = hostname
        self._heaters: List[Any] = []

        # TODO: how to safely close session if one was created here?
        self._session = session if session else aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=CLIENT_TIMEOUT)
        if username is None:
            self._url_base = f"http://{hostname}/"
            self._auth = None
        else:
            self._url_base = f"http://{hostname}/protect/"
            self._auth = aiohttp.BasicAuth(login=username, password=password)

        self.__fake_heater = None
        self._fake_heater: bool = FAKE_HEATER

    @property
    def _fake_heater(self) -> bool:
        """Is there a fake Heater (for testing)."""
        return self.__fake_heater

    @_fake_heater.setter
    def _fake_heater(self, value) -> None:
        """Create a fake Heater (for testing).

        Enable this feature before calling Gateway.heaters().
        """
        self.__fake_heater = value
        if self.__fake_heater:
            _LOGGER.warning(
                "Gateway(%s): fake_heater mode enabled, heater = %s",
                self._hostname,
                FAKE_HEATER_SERIAL,
            )

    @property
    async def heaters(self) -> List[Any]:
        """Retrieve the list of Heaters from the Gateway."""
        if self._heaters != []:
            return self._heaters

        heaters = dict(await self._get("heaterlist.json"))["heaterlist"]

        if self._fake_heater:
            heaters[FAKE_HEATER_INDEX] = FAKE_HEATER_SERIAL

        self._heaters = [Heater(h, idx, self) for idx, h in enumerate(heaters) if h]

        _LOGGER.debug("Gateway(%s).heaters() = %s", self._hostname, heaters)
        return self._heaters


class Heater(InComfortObject):
    """Representation of an InComfort Heater (aka boiler)."""

    def __init__(self, serial_no: str, idx: int, gateway: Gateway) -> None:
        _LOGGER.debug("Heater(serial_no=%s) instantiated.", serial_no)
        super().__init__()

        self._serial_no = serial_no
        self._heater_idx = idx
        self._gateway = gateway

        self._data: Dict[str, Any] = {}
        self._status: Dict[str, Any] = {}
        self._rooms: list = []

        self.__fake_room = None
        self._fake_room: bool = FAKE_ROOM if self._serial_no == FAKE_HEATER_SERIAL else False

    @property
    def _fake_room(self) -> bool:
        """Is there a fake Room (for testing)."""
        return self.__fake_room

    @_fake_room.setter
    def _fake_room(self, value) -> None:
        """Create a fake Room (for testing).

        Enable this feature before calling Heater.update().
        """
        self.__fake_room = value
        if self.__fake_room:
            _LOGGER.warning(
                "Heater(%s): fake_room mode enabled, room = %s.",
                self._serial_no,
                FAKE_ROOM_NUMBER,
            )

    async def update(self) -> None:
        """Retrieve the Heater's latest status from the Gateway."""
        self._data = await self._get(f"data.json?heater={self._heater_idx}")

        self._status = status = {}

        for attr in HEATER_ATTRS:
            status[attr] = getattr(self, attr, None)

        for key in ["nodenr", "rf_message_rssi", "rfstatus_cntr"]:
            status[key] = self._data.get(key)

        _LOGGER.debug("Heater(%s).status() = %s", self._serial_no, status)

    @property
    def status(self) -> dict:
        """Return the current state of the heater."""
        return self._status

    @property
    def display_code(self) -> int:
        """Return the display code, 'displ_code'."""
        return self._data["displ_code"]

    @property
    def display_text(self) -> Optional[str]:
        """Return the display code as text rather than a code."""
        code = self.display_code
        code_map = FAULT_CODES if self.is_failed else DISPLAY_CODES
        return code_map.get(code, f"unknown/other, code = '{code}'")

    @property
    def fault_code(self) -> Optional[int]:
        """Return the fault code when the heater is in a failed state."""
        return self._data["displ_code"] if self.is_failed else None

    @property
    def is_burning(self) -> bool:
        return bool(self._data["IO"] & BITMASK_BURNER)

    @property
    def is_failed(self) -> bool:
        return bool(self._data["IO"] & BITMASK_FAIL)

    @property
    def is_pumping(self) -> bool:
        return bool(self._data["IO"] & BITMASK_PUMP)

    @property
    def is_tapping(self) -> bool:
        return bool(self._data["IO"] & BITMASK_TAP)

    @property
    def heater_temp(self) -> float:
        """Return the supply temperature of the CV (circulating volume)."""
        return _value("ch_temp", self._data)

    @property
    def tap_temp(self) -> float:
        """Return the current temperature of the HW (hot water)."""
        return _value("tap_temp", self._data)

    @property
    def pressure(self) -> float:
        """Return the water pressure of the CH (central heating)."""
        return _value("ch_pressure", self._data)

    @property
    def serial_no(self) -> str:
        """Return the decoded (not reported) serial number of the heater."""
        return self._serial_no

    @property
    def rooms(self) -> List[Any]:
        if self._rooms == []:
            self._rooms = [
                Room(r, self)
                for r in [1, 2]
                if _value(f"room_temp_{r}", self._data) is not None
            ]
        return self._rooms


class Room(InComfortObject):
    """Representation of an InComfort Room."""

    def __init__(self, room_no: int, heater: Heater) -> None:
        _LOGGER.debug("Room(room_no=%s) instantiated.", room_no)
        super().__init__()

        self._gateway = heater._gateway
        self._heater = heater
        self._data: dict = {}

        self.room_no = room_no

    @property
    def status(self) -> Dict[str, Any]:
        """Return the current state of the room."""
        status = {}

        for attr in ROOM_ATTRS:
            status[attr] = getattr(self, attr, None)

        _LOGGER.debug("Room(%s).status() = %s", self.room_no, status)
        return status

    @property
    def room_temp(self) -> Optional[float]:
        """Return the current temperature of the room."""
        return _value(f"room_temp_{self.room_no}", self._heater._data)

    @property
    def setpoint(self) -> Optional[float]:
        """Return the setpoint temperature of the room."""
        return _value(f"room_temp_set_{self.room_no}", self._heater._data)

    @property
    def override(self) -> Optional[float]:
        """Return the override temperature of the room."""
        return _value(f"room_set_ovr_{self.room_no}", self._heater._data)

    async def set_override(self, setpoint: float) -> None:
        _LOGGER.debug("Room(%s).set_override(setpoint=%s)", self.room_no, setpoint)

        try:
            assert OVERRIDE_MIN_TEMP <= setpoint <= OVERRIDE_MAX_TEMP
        except AssertionError:
            raise ValueError(
                "The setpoint is outside of it's valid range, "
                f"{OVERRIDE_MIN_TEMP}-{OVERRIDE_MAX_TEMP}."
            )

        url = "data.json?heater={self._heater._heater_idx}"
        url += f"&thermostat={int(self.room_no) - 1}"
        url += f"&setpoint={int((setpoint - OVERRIDE_MIN_TEMP) * 10)}"
        await self._get(url)
