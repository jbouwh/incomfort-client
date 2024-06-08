#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

Each Gateway can have up to 8 Heaters (boilers) and each Heater can have 0-2
active Room thermostats.
"""

from __future__ import annotations

import logging

import aiohttp

__version__ = "0.5.0"

NULL_SERIAL_NO = "000W00000"
HEATERLIST = "heaterlist"

CLIENT_TIMEOUT = 20  # seconds

INVALID_VALUE = (2**15 - 1) / 100.0  # 127 * 256 + 255 = 327.67
SERIAL_LINE = "0123456789abcdefghijklmnopqrstuvwxyz"

# key label: IO (is a bitmask)
BITMASK_BURNER = 0x08  # burner state: on / off
BITMASK_FAIL = 0x01  # failure state: on / off (aka lockout)
BITMASK_PUMP = 0x02  # pump state: on / off
BITMASK_TAP = 0x04  # tap (DHW) state: function on / off

# key label: displ_code
DISPLAY_CODES: list[int, str] = {
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
FAULT_CODES: list[int, str] = {
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

HEATER_ATTRS: tuple[str] = (
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
)
HEATER_ATTRS_RAW: tuple[str] = ("nodenr", "rf_message_rssi", "rfstatus_cntr")

ROOM_ATTRS: tuple[str] = ("room_temp", "setpoint", "override")

OVERRIDE_MAX_TEMP = 30.0
OVERRIDE_MIN_TEMP = 5.0

_LOGGER = logging.getLogger(__name__)

# pylint: disable=protected-access, missing-docstring


def _value(key_stub: str, data_dict: dict) -> None | float:
    def _convert(most_significant_byte: int, least_significant_byte: int) -> float:
        return (most_significant_byte * 256 + least_significant_byte) / 100.0

    _value = _convert(data_dict[key_stub + "_msb"], data_dict[key_stub + "_lsb"])
    return _value if _value != INVALID_VALUE else None


class IncomfortError(Exception):
    """Base class for InComfor exceptions."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message = args[0] if args else None


class InvalidGateway(IncomfortError):
    def __str__(self) -> str:
        err_msg = "Invalid/No reponse from Gateway"
        err_tip = "(check the network/hostname, and the user credentials)"
        if self.message:
            return f"{err_msg}: {self.message} {err_tip}"
        return f"{err_msg} {err_tip}"


class InvalidHeaterList(IncomfortError):
    def __str__(self) -> str:
        err_msg = "There is no valid Heater in the heaterlist"
        err_tip = "(check the binding between the gateway and the heater)"
        if self.message:
            return f"{err_msg}: {self.message} {err_tip}"
        return f"{err_msg} {err_tip}"


class IncomfortObject:
    """Base for InComfortObjects."""

    def __init__(self) -> None:
        self._gateway: Gateway = None

    async def _get(self, url: str):
        _LOGGER.debug(
            "_get(url=%s, auth=%s)", url, "REDACTED" if self._gateway._auth else None
        )

        async with self._gateway._session.get(
            url=f"{self._gateway._url_base}{url}",
            auth=self._gateway._auth,
            raise_for_status=True,
            timeout=self._gateway._timeout,
        ) as resp:
            response = await resp.json(content_type=None)

        _LOGGER.debug("_get(url=%s): response = %s", url, response)
        return response


class Gateway(IncomfortObject):
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
        self._heaters: None | list[Heater] = None

        # TODO: how to safely close session if one was created here?
        self._session = session if session else aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=CLIENT_TIMEOUT)
        if username is None:
            self._url_base = f"http://{hostname}/"
            self._auth = None
        else:
            self._url_base = f"http://{hostname}/protect/"
            self._auth = aiohttp.BasicAuth(login=username, password=password)

    # FIXME CC: heaters = incomfort_data["heaters"] = list(await client.heaters())
    async def heaters(self, force_refresh: bool = None) -> list[Heater]:
        """Retrieve the list of Heaters from the Gateway."""
        if self._heaters is not None and not force_refresh:
            return self._heaters

        try:
            heaters = dict(await self._get("heaterlist.json"))[HEATERLIST]
        except aiohttp.ClientError as exc:
            raise InvalidGateway(exc) from exc

        self._heaters = [
            Heater(h, idx, self)
            for idx, h in enumerate(heaters)
            if h and h != NULL_SERIAL_NO
        ]

        _LOGGER.debug("Gateway(%s).heaters() = %s", self._hostname, heaters)
        if self._heaters == []:
            raise InvalidHeaterList

        return self._heaters


class Heater(IncomfortObject):
    """Representation of an InComfort Heater (aka boiler)."""

    def __init__(self, serial_no: str, idx: int, gateway: Gateway) -> None:
        _LOGGER.debug("Heater(serial_no=%s) instantiated.", serial_no)
        super().__init__()

        self._serial_no: str = serial_no
        self._heater_idx: int = idx
        self._gateway: Gateway = gateway

        self._data: dict = {}
        self._status: dict = {}
        self._rooms: list[Room] = None

    async def update(self) -> None:
        """Retrieve the Heater's latest status from the Gateway."""
        self._data = await self._get(f"data.json?heater={self._heater_idx}")

        self._status = {}

        for attr in HEATER_ATTRS:
            self._status[attr] = getattr(self, attr, None)

        for key in HEATER_ATTRS_RAW:
            self._status[key] = self._data.get(key)

        _LOGGER.debug("Heater(%s).status() = %s", self._serial_no, self._status)

    @property
    def status(self) -> dict:
        """Return the current state of the heater."""
        return self._status

    @property
    def display_code(self) -> int:
        """Return the display code, 'displ_code'."""
        return self._data["displ_code"]

    @property
    def display_text(self) -> None | str:
        """Return the display code as text rather than a code."""
        code = self.display_code
        code_map = FAULT_CODES if self.is_failed else DISPLAY_CODES
        return code_map.get(code, f"unknown/other, code = '{code}'")

    @property
    def fault_code(self) -> None | int:
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
        """Return the reported (not decoded) serial number of the heater."""
        return self._serial_no

    @property
    def rooms(self) -> list[Room]:
        if self._rooms is None:
            self._rooms = [
                Room(r, self)
                for r in (1, 2)
                if _value(f"room_temp_{r}", self._data) is not None
            ]
        return self._rooms


class Room(IncomfortObject):
    """Representation of an InComfort Room."""

    def __init__(self, room_no: int, heater: Heater) -> None:
        _LOGGER.debug("Room(room_no=%s) instantiated.", room_no)
        super().__init__()

        self._gateway = heater._gateway
        self._heater = heater
        self._data: dict = {}

        self.room_no = room_no

    @property
    def status(self) -> dict:
        """Return the current state of the room."""
        status = {}

        for attr in ROOM_ATTRS:
            status[attr] = getattr(self, attr, None)

        _LOGGER.debug("Room(%s).status() = %s", self.room_no, status)
        return status

    @property
    def room_temp(self) -> None | float:
        """Return the current temperature of the room."""
        return _value(f"room_temp_{self.room_no}", self._heater._data)

    @property
    def setpoint(self) -> None | float:
        """Return the setpoint temperature of the room."""
        return _value(f"room_temp_set_{self.room_no}", self._heater._data)

    @property
    def override(self) -> None | float:
        """Return the override temperature of the room."""
        return _value(f"room_set_ovr_{self.room_no}", self._heater._data)

    async def set_override(self, setpoint: float) -> None:
        _LOGGER.debug("Room(%s).set_override(setpoint=%s)", self.room_no, setpoint)

        try:
            assert OVERRIDE_MIN_TEMP <= setpoint <= OVERRIDE_MAX_TEMP
        except AssertionError as exc:
            raise ValueError(
                "The setpoint is outside of it's valid range, "
                f"{OVERRIDE_MIN_TEMP}-{OVERRIDE_MAX_TEMP}."
            ) from exc

        url = "data.json?heater={self._heater._heater_idx}"
        url += f"&thermostat={int(self.room_no) - 1}"
        url += f"&setpoint={int((setpoint - OVERRIDE_MIN_TEMP) * 10)}"
        await self._get(url)
