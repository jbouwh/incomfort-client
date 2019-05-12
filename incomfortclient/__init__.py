"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

   Each Gateway can have up to 8 Heaters (Boilers) and each Heater can have 0-2
   Room thermostats.
   """

import asyncio
import logging

import aiohttp

INVALID_VALUE = (2**15-1)/100.0  # 327.67

SERIAL_LINE = '0123456789abcdefghijklmnopqrstuvwxyz'

# key label: IO
BITMASK_BURNER = 0x08  # burner state: on / off
BITMASK_FAIL = 0x01  # failure state: on / off (aka lockout)
BITMASK_PUMP = 0x02  # pump state: on / off
BITMASK_TAP = 0x04  # tap (DHW) state: function on / off

# key label: displ_code
DISPLAY_CODES = {
    0: 'opentherm',
    15: 'boiler ext.',
    24: 'frost',
    37: 'central heating rf',
    51: 'tapwater int.',
    85: 'sensortest',
    102: 'central heating',
    126: 'standby',
    153: 'postrun boiler',
    170: 'service',
    204: 'tapwater',
    231: 'postrun ch',
    240: 'boiler int.',
    255: 'buffer'
}

DEFAULT_HEATER_NO = 0
DEFAULT_ROOM_NO = 0
OVERRIDE_MAX_TEMP = 30.0
OVERRIDE_MIN_TEMP = 5.0

_LOGGER = logging.getLogger(__name__)

# pylint: disable=protected-access, fixme, missing-docstring

def _value(key_stub: str, data_dict: dict) -> float:
    def _convert(most_significant_byte: int,
                 least_significant_byte: int) -> float:
        return (most_significant_byte * 256 + least_significant_byte) / 100.0

    _value = _convert(data_dict[key_stub + '_msb'],
                      data_dict[key_stub + '_lsb'])
    return _value if _value != INVALID_VALUE else None


class InComfortObject(object):
    """Base for InComfortObjects."""

    def __init__(self):
        self._gateway = None

    async def _get(self, url: str):
        _LOGGER.debug("_get(url=%s, _auth=%s)", url, self._gateway._auth)

        async with self._gateway._session.get(
            url,
            auth=self._gateway._auth,
            raise_for_status=True,
            timeout=self._gateway._timeout,
        ) as response:
            _LOGGER.debug("_get(url), response.status=%s", response.status)
            response = await response.json(content_type=None)

        _LOGGER.debug("_get(url=%s): response = %s", url, response)
        return response


class Gateway(InComfortObject):
    """Representation of an InComfort Gateway."""

    def __init__(self, hostname: str, username: str = None,
                 password: str = None, session: aiohttp.ClientSession = None):
        _LOGGER.debug("Gateway.__init__(hostname=%s)", hostname)
        super().__init__()

        self._gateway = self

        # TODO: how to close session on object destruction if we created one?
        self._session = session  # if session else aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=10)
        if username is None:
            self._url_base = 'http://{0}/'.format(hostname)
            self._auth = None
        else:
            self._url_base = 'http://{0}/protect/'.format(hostname)
            self._auth = aiohttp.BasicAuth(login=username, password=password)

    @property
    async def heaters(self) -> list:
        _LOGGER.debug("Gateway.heaters")

        url = '{}heaterlist.json'.format(self._url_base)
        heaters = await self._get(url)

        return [Heater(h, self)
                for h in heaters['heaterlist'] if h]


class Heater(InComfortObject):
    """Representation of an InComfort Heater."""

    def __init__(self, serial_no: str, gateway: Gateway):
        _LOGGER.debug("Heater.__init__(serial_no=%s)", serial_no)
        super().__init__()

        self._gateway = gateway
        self._serial_no = serial_no
        self._data = None

    async def update(self):
        """Retrieve the Heater's status from the Gateway.

        GET http://<ip address>/data.json?heater=<nr>
        """
        _LOGGER.debug("update()")

        url = '{}data.json?heater={}'.format(
            self._gateway._url_base, DEFAULT_HEATER_NO)
        self._data = await self._get(url)

    @property
    def status(self) -> dict:
        """Return the current state of the heater."""
        status = {}

        status['display_code'] = self.display_code if self._data else None
        status['display_text'] = self.display_text if self._data else None
        status['fault_code'] = self.fault_code if self._data else None

        status['is_burning'] = self.is_burning if self._data else None
        status['is_failed'] = self.is_failed if self._data else None
        status['is_pumping'] = self.is_pumping if self._data else None
        status['is_tapping'] = self.is_tapping if self._data else None

        status['heater_temp'] = self.heater_temp if self._data else None
        status['tap_temp'] = self.tap_temp if self._data else None
        status['pressure'] = self.pressure if self._data else None

        status['serial_no'] = self.serial_no if self._data else None

        status['nodenr'] = self._data['nodenr'] if self._data else None
        status['rf_message_rssi'] = self._data['rf_message_rssi'] if self._data else None
        status['rfstatus_cntr'] = self._data['rfstatus_cntr'] if self._data else None

        _LOGGER.debug("status() = %s", status)
        return status

    @property
    def display_text(self) -> str:
        """Return the display code as a string rather than a number.

        If the heater is in a failed state, this will be the 'fault_code'.
        """
        _code = self._data['displ_code']
        return DISPLAY_CODES.get(
            _code,
            "unknown/other, code = {0} (fault code?)".format(_code)
        )

    @property
    def display_code(self) -> int:
        """Return the display code, displ_code.

        If the heater is in a failed state, this will be the fault_code.
        """
        return self._data['displ_code']

    @property
    def fault_code(self) -> int:
        _code = self._data['displ_code']
        return _code if self.is_failed else 0

    @property
    def is_burning(self) -> bool:
        return bool(self._data['IO'] & BITMASK_BURNER)

    @property
    def is_failed(self) -> bool:
        return bool(self._data['IO'] & BITMASK_FAIL)

    @property
    def is_pumping(self) -> bool:
        return bool(self._data['IO'] & BITMASK_PUMP)

    @property
    def is_tapping(self) -> bool:
        return bool(self._data['IO'] & BITMASK_TAP)

    @property
    def heater_temp(self) -> float:
        """Return the supply temperature of the CV (circulating volume)."""
        return _value('ch_temp', self._data)

    @property
    def tap_temp(self) -> float:
        """Return the current temperature of the HW (hot water)."""
        return _value('tap_temp', self._data)

    @property
    def pressure(self) -> float:
        """Return the water pressure of the CH (central heating)."""
        return _value('ch_pressure', self._data)

    @property
    def serial_no(self) -> str:
        """Return the serial number of the heater."""
        return (str(self._data['serial_year']) +
                str(self._data['serial_month']) +
                SERIAL_LINE[self._data['serial_line']] +
                str(self._data['serial_sn1']) +
                str(self._data['serial_sn2']) +
                str(self._data['serial_sn3']))

    @property
    def rooms(self) -> list:
        return [Room(r, self) for r in ['1', '2']
                if _value('room_temp_{}'.format(r), self._data) is not None]


class Room(InComfortObject):
    """Representation of an InComfort Room."""

    def __init__(self, room_no: int, heater: Heater):
        _LOGGER.debug("Room.__init__(room_no=%s)", room_no)
        super().__init__()

        self.room_no = room_no
        self._heater = heater
        self._gateway = heater._gateway

        self._data = heater._data

    @property
    def status(self) -> dict:
        """Return the current state of the room."""
        status = {}

        status['room_temp'] = self.room_temp if self._data else None
        status['setpoint'] = self.setpoint if self._data else None
        status['override'] = self.override if self._data else None

        _LOGGER.debug("status() = %s", status)
        return status

    @property
    def room_temp(self) -> float:
        """Return the current temperature of the room."""
        return _value('room_temp_{}'.format(self.room_no), self._data)

    @property
    def setpoint(self) -> float:
        """Return the (scheduled?) setpoint temperature of the room."""
        return _value('room_temp_set_{}'.format(self.room_no), self._data)

    @property
    def override(self) -> float:
        """Return the override setpoint temperature of the room."""
        return _value('room_set_ovr_{}'.format(self.room_no), self._data)

    async def set_override(self, setpoint: float) -> None:
        _LOGGER.debug("Room(%s).set_override(setpoint=%s)",
                      self.room_no, setpoint)

        setpoint = min(max(setpoint, OVERRIDE_MIN_TEMP), OVERRIDE_MAX_TEMP)
        url = '{}data.json?heater={}&thermostat={}&setpoint={}'.format(
            self._gateway._url_base,
            DEFAULT_HEATER_NO,
            int(self.room_no) - 1,
            int((setpoint - OVERRIDE_MIN_TEMP) * 10)
        )
        await self._get(url)


async def main(loop):
    import argparse
    _LOGGER.debug("main()")

    parser = argparse.ArgumentParser()

    parser.add_argument("gateway",
                        help="hostname/address of the InComfort gateway")

    credentials_group = parser.add_argument_group(
        "user credentials - used only for newer firmwares")
    credentials_group.add_argument(
        "-u", "--username", type=str, required=False, default=None)
    credentials_group.add_argument(
        "-p", "--password", type=str, required=False, default=None)

    parser.add_argument("-t", "--temp", type=float, required=False,
                        help="set room temperature (in C, no default)")
    parser.add_argument("-r", "--raw", action='store_true', required=False,
                        help="return raw JSON, useful for testing")

    args = parser.parse_args()

    if bool(args.username) ^ bool(args.password):
        parser.error("--username and --password must be given together, "
                     "or not at all")

    async with aiohttp.ClientSession() as session:
        gateway = Gateway(args.gateway, session=session,
                          username=args.username, password=args.password)
        try:
            heater = list(await gateway.heaters)[DEFAULT_HEATER_NO]
        except aiohttp.client_exceptions.ClientResponseError:
            _LOGGER.error("ClientResponseError Hint: Bad user credentials")
            raise

        await heater.update()

        if args.temp:
            try:
                await heater.rooms[DEFAULT_ROOM_NO].set_override(args.temp)
            except IndexError:
                _LOGGER.error(
                    "IndexError Hint: There is no valid room thermostat")
                raise

        elif args.raw:
            print(heater._data)  # raw JSON

        else:
            status = dict(heater.status)
            for room in heater.rooms:
                status['room_{}'.format(room.room_no)] = room.status
            print(status)


# called from CLI? python itclient.py <hostname/address> [--temp <int>]
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
