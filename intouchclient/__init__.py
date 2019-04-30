"""Python client library for the InterGas InTouch system (via Lan2RF gateway).

   Each Gateway can have up to 8 Heaters (Boilers) and each Heater can have 0-2
   Room thermostats.
   """

import asyncio
import logging

import aiohttp

INVALID_VALUE = (2**15-1)/100.0

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

HTTP_OK = 200  # cheaper than: HTTPStatus.OK

_LOGGER = logging.getLogger(__name__)


def _convert(most_significant_byte, least_significant_byte) -> float:
    _value = (most_significant_byte * 256 + least_significant_byte) / 100.0

    return _value if _value != INVALID_VALUE else None


class InTouchObject(object):
    async def _get(self, url):
        _LOGGER.debug("_get(url=%s)", url)

        async with self._gateway._session.get(
            url,
            timeout=self._gateway._timeout,
            auth=self._gateway._auth
        ) as response:
            assert response.status == HTTP_OK
            response = await response.json(content_type=None)

        _LOGGER.debug("_get(url=%s): response = %s", url, response)
        return response


class InTouchGateway(InTouchObject):
    def __init__(self, hostname, session, username=None, password=None,
                 debug=False):
        if debug is True:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")
        else:
            _LOGGER.debug("Debug mode is not explicitly enabled "
                          "(but may be enabled elsewhere).")

        _LOGGER.info("InTouchGateway.__init__()")

        self._hostname = 'http://{0}/'.format(hostname)
        self._gateway = self

        # TODO: how to close session on object destruction if we created one?
        self._session = session  # if session else aiohttp.ClientSession()
        self._timeout = aiohttp.ClientTimeout(total=10)
        if username is None:
            self._auth = None
        else:
            self._auth = aiohttp.BasicAuth(login=username, password=password)

    @property
    async def heaters(self) -> list:
        _LOGGER.debug("InTouchGateway.heaters")

        url = '{}heaterlist.json'.format(self._hostname)
        heaters = await self._get(url)

        return [InTouchHeater(h, self)
                for h in heaters['heaterlist'] if h]


class InTouchHeater(InTouchObject):
    def __init__(self, serial_no, gateway):

        _LOGGER.debug("InTouchHeater.__init__(serial_no=%s)", serial_no)

        self._gateway = gateway
        self._serial_no = serial_no
        self._data = None

    async def update(self):
        """Retrieve the Heater's status from the Gateway.

        GET http://<ip address>/data.json?heater=<nr>
        """
        _LOGGER.debug("update()")

        url = '{}data.json?heater={}'.format(self._gateway._hostname, 0)
        self._data = await self._get(url)

    @property
    def status(self) -> dict:
        """Return the current state of the heater."""
        status = {}

        status['display_code'] = self.display_code
        status['display_text'] = self.display_text
        status['fault_code'] = self.fault_code

        status['is_burning'] = self.is_burning
        status['is_failed'] = self.is_failed
        status['is_pumping'] = self.is_pumping
        status['is_tapping'] = self.is_tapping

        status['heater_temp'] = self.heater_temp
        status['tap_temp'] = self.tap_temp
        status['pressure'] = self.pressure

        status['serial_no'] = self.serial_no

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
        return _convert(self._data['ch_temp_msb'],
                        self._data['ch_temp_lsb'])

    @property
    def tap_temp(self) -> float:
        """Return the current temperature of the HW (hot water)."""
        return _convert(self._data['tap_temp_msb'],
                        self._data['tap_temp_lsb'])

    @property
    def pressure(self) -> float:
        """Return the water pressure of the CH (central heating)."""
        return _convert(self._data['ch_pressure_msb'],
                        self._data['ch_pressure_lsb'])

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
        return [InTouchRoom(r, self) for r in ['1', '2']
                if _convert(
                    self._data['room_temp_{}_msb'.format(r)],
                    self._data['room_temp_{}_lsb'.format(r)]) is not None]


class InTouchRoom(InTouchObject):
    def __init__(self, room_no, heater):
        _LOGGER.debug("InTouchRoom.__init__(room_no=%s)", room_no)

        self.room_no = room_no
        self._heater = heater
        self._gateway = heater._gateway

        self._data = heater._data

    @property
    def status(self) -> dict:
        """Return the current state of the room."""
        status = {}

        status['room_temp'] = self.room_temp
        status['setpoint'] = self.setpoint
        status['override'] = self.override

        _LOGGER.debug("status() = %s", status)
        return status

    @property
    def room_temp(self) -> float:
        """Return the current temperature of the room."""
        return _convert(
            self._data['room_temp_{}_msb'.format(self.room_no)],
            self._data['room_temp_{}_lsb'.format(self.room_no)])

    @property
    def setpoint(self) -> float:
        """Return the (scheduled?) setpoint temperature of the room."""
        return _convert(
            self._data['room_temp_set_{}_msb'.format(self.room_no)],
            self._data['room_temp_set_{}_lsb'.format(self.room_no)])

    @property
    def override(self) -> float:
        """Return the override setpoint temperature of the room."""
        return _convert(
            self._data['room_set_ovr_{}_msb'.format(self.room_no)],
            self._data['room_set_ovr_{}_lsb'.format(self.room_no)])

    async def set_override(self, setpoint):
        url = '{}data.json?heater={}&thermostat={}&setpoint={}'.format(
            self._gateway._hostname,
            0,
            self.room_no,
            int((min(max(setpoint, 5), 30) - 5.0) * 10))

        await self._get(url)


async def main(loop):
    import argparse
    _LOGGER.debug("main()")

    parser = argparse.ArgumentParser()

    parser.add_argument("gateway",
                        help="hostname/address of the InTouch gateway")
    parser.add_argument("-t", "--temp", type=float, required=False,
                        help="set room[0] temperature (in C, no default)")

    args = parser.parse_args()

    async with aiohttp.ClientSession() as session:
        gateway = InTouchGateway(args.gateway, session)
        heaters = await gateway.heaters

        await heaters[0].update()

        if args.temp:
            await heaters[0].rooms[0].set_override(args.temp)

    if not args.temp:
        print(heaters[0].status)
        for room in heaters[0].rooms:
            print(room.status)


# called from CLI? python itclient.py <hostname/address> [--temp <int>]
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
