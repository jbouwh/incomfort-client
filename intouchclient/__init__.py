"""Python client library for the InterGas InTouch system (via Lan2RF gateway).

   Each Gateway can have multiple InTouch Heaters (Boilers), each Heater can
   have 1-2 Thermostats.
   """

# Based upon: https://github.com/bwesterb/incomfort, and so uses the same
# methods and properties, where possible.

import asyncio
import logging

import aiohttp
# from http import HTTPStatus

HTTP_OK = 200

INVALID_VALUE = (2**15-1)/100.0
SERIAL_LINE = '0123456789abcdefghijklmnopqrstuvwxyz'

# key label: IO
BITMASK_BURNER = 0x08  # burner state: on / off
BITMASK_FAIL = 0x01  # failure state: on / off
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

_LOGGER = logging.getLogger(__name__)


def _convert(MostSignificantByte, LeastSignificantByte) -> float:
    _value = (MostSignificantByte * 256 + LeastSignificantByte) / 100.0
    return _value if _value is not INVALID_VALUE else None


async def async_get(session, url):
    _LOGGER.debug("async_get(session, url=%s)", url)

    async with session.get(url) as response:
        assert response.status == HTTP_OK  # cheaper than: HTTPStatus.OK
        return await response.json(content_type=None)


class InComfortClient(object):
    def __init__(self):
        pass


class Gateway(InComfortClient):
    def __init__(self, hostname):

        _LOGGER.debug("__init__(hostname=%s)", hostname)

        self._name = hostname
        self._data = None

#       await self.async_status()
        self.async_status()

#   async def async_status(self, heater=0):
    def async_status(self, heater=0):
        """Retrieve the Heater's status from the Gateway.

        GET <ip address>/data.json?heater=<nr>
        """
        _LOGGER.debug("async_status(heater=%s)", heater)

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = 'http://{0}/data.json?heater=0'.format(self._name)
            self._data = await async_get(session, url)

        _LOGGER.debug("async_status(heater=%s) = ", self._data)

    @property
    def _status(self) -> dict:
        """Return the current state of the heater."""
        return dict(self._data)

    @property
    def status(self) -> dict:
        """Return the current state of the heater."""
        _LOGGER.debug("status()")
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
        return _code if self.is_failed else None

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
        """Return the supply temperature of the CH/CV (circulating volume)."""
        return _convert(self._data['ch_temp_msb'],
                        self._data['ch_temp_lsb'])

    @property
    def tap_temp(self) -> float:
        """Return the current temperature of the tap (HW, hot water)."""
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
        return \
            str(self._data['serial_year']) + \
            str(self._data['serial_month']) + \
            SERIAL_LINE[self._data['serial_line']] + \
            str(self._data['serial_sn1']) + \
            str(self._data['serial_sn2']) + \
            str(self._data['serial_sn3'])


# python intouch.py [--raw] hostname/address
async def main(loop):
    _LOGGER.debug("main()")

    parser = argparse.ArgumentParser()

    parser.add_argument("gateway",
                        help="hostname/address of the InComfort gateway")
    parser.add_argument("-r", "--raw", action='store_true', required=False,
                        help="return the raw data")

#   args = vars(parser.parse_args())
    args = parser.parse_args()

    gateway = Gateway(args.gateway)

    if args.raw:
        print(gateway._status)
    else:
        print(gateway.status)


# called from CLI?
if __name__ == '__main__':
    import argparse

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    loop.close()
