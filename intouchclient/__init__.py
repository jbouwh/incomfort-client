"""Python client library for the InterGas InTouch system (via Lan2RF gateway).

   Each Gateway can have multiple InTouch Heaters (Boilers), each Heater can
   have 1-2 Thermostats.
   """

# Based upon: https://github.com/bwesterb/incomfort, and so uses the same
# methods and properties, where possible.

import asyncio
import logging

import aiohttp

INVALID_TEMP = (2**15-1)/100.0

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
    return _value if _value is not INVALID_TEMP else None


async def _get(url, session):
    _LOGGER.debug("_get(url=%s)", url)

    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=10)
    ) as response:
        assert response.status == HTTP_OK
        response = await response.json(content_type=None)

    _LOGGER.warn("_get(url=%s): response = %s", url, response)
    return response


class InComfortGateway(object):
    def __init__(self, hostname, session=None, debug=False):
        if debug is True:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("Debug mode is explicitly enabled.")
        else:
            _LOGGER.debug("Debug mode is not explicitly enabled "
                          "(but may be enabled elsewhere).")

        _LOGGER.info("InComfortGateway.__init__()")

        self._name = hostname

        # TODO: use existing session if one was provided (needs fixing)
        self._session = session if session else aiohttp.ClientSession()

    @property
    async def heaterlist(self) -> list:
        # {"heaterlist":["1709t023082",null,null,null,null,null,null,null]}
        _LOGGER.debug("InComfortGateway.heaterlist")

        url = 'http://{0}/heaterlist.json'.format(self._name)
        heaterlist = await _get(url, self._session)

        return [InComfortHeater(h, self)
                for h in heaterlist['heaterlist'] if h]


class InComfortHeater(object):
    def __init__(self, serial_no, gateway):

        _LOGGER.debug("InComfortHeater.__init__(serial_no=%s)", serial_no)

        self._gateway = gateway
        self._serial_no = serial_no
        self._data = None

    async def update(self):
        """Retrieve the Heater's status from the Gateway.

        GET http://<ip address>/data.json?heater=<nr>
        """
        _LOGGER.debug("update()")

        url = 'http://{0}/data.json?heater=0'.format(self._gateway._name)
        self._data = await _get(url, self._gateway._session)

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
        status['is_tap_on'] = self.is_tap_on

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
    def is_tap_on(self) -> bool:
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
    def roomlist(self) -> list:
        return [InComfortRoom('1', self, self._gateway),
                InComfortRoom('2', self, self._gateway)]


class InComfortRoom(object):
    def __init__(self, room_no, heater, gateway):
        _LOGGER.debug("InComfortRoom.__init__(room_no=%s)", room_no)

        self._gateway = gateway
        self._heater = heater
        self.room_no = room_no

        self._data = heater._data

    @property
    def status(self) -> dict:
        """Return the current state of the room."""
        status = {}

        status['temperature'] = self.temperature
        status['setpoint'] = self.setpoint
        status['override'] = self.override

        _LOGGER.debug("status() = %s", status)
        return status

    @property
    def temperature(self) -> float:
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
        url = 'http://{}/data.json?heater=0&thermostat={}&setpoint={}'.format(
            self._gateway._name,
            self.room_no,
            int((min(max(setpoint, 5), 30) - 5.0) * 10))

        response = await _get(url, self._gateway._session)


async def main(loop):
    import argparse
    _LOGGER.debug("main()")

    parser = argparse.ArgumentParser()

    parser.add_argument("gateway",
                        help="hostname/address of the InComfort gateway")
    parser.add_argument("-r", "--raw", action='store_true', required=False,
                        help="return the raw data")

    args = parser.parse_args()

    # TODO: provide a session (needs fixing)
    session = aiohttp.ClientSession()

    gateway = InComfortGateway(args.gateway, session=session)
    heaterlist = await gateway.heaterlist

    await heaterlist[0].update()
    # print(heaterlist[0].status)
    # print(heaterlist[0].roomlist[1].status)

    if args.raw:
        print(heaterlist[0]._status)
    else:
        print(heaterlist[0].status)

    await session.close()

# called from CLI? python intouch.py [--raw] hostname/address
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
