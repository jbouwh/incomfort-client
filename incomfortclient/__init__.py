"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

   Each Gateway can have up to 8 Heaters (boilers) and each Heater can have 0-2
   Room thermostats.
   """

import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

import aiohttp

DEBUG_MODE = False
FAKE_ROOM = False

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

DEFAULT_HEATER_NO = 0
DEFAULT_ROOM_NO = 0
OVERRIDE_MAX_TEMP = 30.0
OVERRIDE_MIN_TEMP = 5.0

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

if DEBUG_MODE is True:
    import ptvsd  # pylint: disable=import-error

    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.info("Waiting for debugger to attach...")
    ptvsd.enable_attach(address=("172.27.0.138", 5679), redirect_output=True)
    ptvsd.wait_for_attach()
    _LOGGER.info("Debugger is attached!")


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

        # if enabled, inject a fake current temperature
        if "room_temp_2_msb" in response and self._fake_room:
            temp = 5 + random.randint(0, 8)
            response.update({"room_temp_2_msb": temp})
            response.update({"room_temp_2_lsb": 0})

            response.update({"room_temp_set_2_msb": 7})
            response.update({"room_temp_set_2_lsb": 158})

            _LOGGER.info(
                "room_2 faked: temperature=%s, setpoint=%s",
                _value(f"room_temp_2", response),  # 12.80-33.28C
                _value(f"room_temp_set_2", response),  # 19.50C
            )

        _LOGGER.debug("_get(url=%s): response = %s", url, response)
        return response


class Gateway(InComfortObject):
    """Representation of an InComfort Gateway."""

    def __init__(
        self,
        hostname: str,
        username: str = None,
        password: str = None,
        session: aiohttp.ClientSession = None,
        fake_room=FAKE_ROOM,
    ) -> None:
        _LOGGER.debug("Gateway(hostname=%s) instantiated.", hostname)
        super().__init__()

        self._gateway = self
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

        self._fake_room = fake_room

    @property
    async def heaters(self) -> List[Any]:
        if self._heaters == []:
            heaters = await self._get("heaterlist.json")

            self._heaters = [Heater(h, self) for h in heaters["heaterlist"] if h]

        self._heaters[0].fake_room = self._fake_room

        return self._heaters


class Heater(InComfortObject):
    """Representation of an InComfort Heater."""

    def __init__(self, serial_no: str, gateway: Gateway) -> None:
        _LOGGER.debug("Heater(serial_no=%s) instantiated.", serial_no)
        super().__init__()

        self._serial_no = serial_no
        self._gateway = gateway

        self._data: Dict[str, Any] = {}
        self._status: Dict[str, Any] = {}
        self._fake_room = False
        self._rooms: list = []

    @property
    def fake_room(self) -> bool:
        """Create a fake room (for testing)."""
        return self._fake_room

    @fake_room.setter
    def fake_room(self, value) -> None:
        self._fake_room = value
        if self._fake_room:
            _LOGGER.warning("Heater(%s): fake_room mode is enabled", self._serial_no)

    async def update(self) -> None:
        """Retrieve the Heater's status from the Gateway."""
        self._data = await self._get(f"data.json?heater={DEFAULT_HEATER_NO}")

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
        """Return the display code, displ_code.

        If the heater is in a failed state, this will be the fault_code.
        """
        return self._data["displ_code"]

    @property
    def display_text(self) -> str:
        """Return the display code as a string rather than a number."""
        _code = self._data["displ_code"]
        return DISPLAY_CODES.get(_code, f"unknown/other, code = {_code} (fault code?)")

    @property
    def fault_code(self) -> int:
        _code = self._data["displ_code"]
        return _code if self.is_failed else 0

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
        return (
            str(self._data["serial_year"])
            + str(self._data["serial_month"])
            + SERIAL_LINE[self._data["serial_line"]]
            + str(self._data["serial_sn1"])
            + str(self._data["serial_sn2"])
            + str(self._data["serial_sn3"])
        )  # should be the same as: self._serial_no

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

        url = "data.json?heater={DEFAULT_HEATER_NO}"
        url += f"&thermostat={int(self.room_no) - 1}"
        url += f"&setpoint={int((setpoint - OVERRIDE_MIN_TEMP) * 10)}"
        await self._get(url)


async def main(loop) -> None:
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("gateway", help="hostname/address of the InComfort gateway")

    credentials_group = parser.add_argument_group(
        "user credentials - used only for newer firmwares"
    )
    credentials_group.add_argument(
        "-u", "--username", type=str, required=False, default=None
    )
    credentials_group.add_argument(
        "-p", "--password", type=str, required=False, default=None
    )

    parser.add_argument(
        "-t",
        "--temp",
        type=float,
        required=False,
        help="set room temperature (in C, no default)",
    )
    parser.add_argument(
        "-r",
        "--raw",
        action="store_true",
        required=False,
        help="return raw JSON, useful for testing",
    )

    args = parser.parse_args()

    if bool(args.username) ^ bool(args.password):
        parser.error("--username and --password must be given together, or not at all")

    async with aiohttp.ClientSession() as session:
        gateway = Gateway(
            args.gateway,
            session=session,
            username=args.username,
            password=args.password,
        )
        try:
            heater = list(await gateway.heaters)[DEFAULT_HEATER_NO]
        except aiohttp.client_exceptions.ClientResponseError:
            _LOGGER.error("ClientResponseError - Hint: Check the user credentials")
            raise

        await heater.update()

        if args.temp:
            try:
                await heater.rooms[DEFAULT_ROOM_NO].set_override(args.temp)
            except IndexError:
                _LOGGER.error("IndexError - Hint: There is no valid room thermostat")
                raise

        elif args.raw:
            print(heater._data)  # raw JSON

        else:
            status = dict(heater.status)
            for room in heater.rooms:
                status[f"room_{room.room_no}"] = room.status
            print(status)


# called from CLI?
if __name__ == "__main__":  # called from CLI?
    LOOP = asyncio.get_event_loop()
    LOOP.run_until_complete(main(LOOP))
    LOOP.close()
