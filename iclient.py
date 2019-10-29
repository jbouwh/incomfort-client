"""
Usage: iclient.py GATEWAY [(--user=USERNAME --pass=PASSWORD)]

Connect to an Intergas Lan2RF gateway obtain Heater state data.

Arguments:
  GATEWAY the hostname/address of an Lan2RF gateway

 Options:
  Some Lan2RF gateways require user credentials:
    -u USERNAME --user=USERNAME    the username
    -p PASSWORD --pass=PASSWORD    the password

"""

import asyncio
import logging

import aiohttp
from docopt import docopt

from incomfortclient import Gateway as InComfortGateway

logging.basicConfig(datefmt="%H:%M:%S", format="%(asctime)s %(levelname)s: %(message)s")
_LOGGER = logging.getLogger(__name__)

DEBUG_MODE = True

if DEBUG_MODE is True:
    import ptvsd  # pylint: disable=import-error

    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.info("Waiting for debugger to attach...")
    ptvsd.enable_attach(address=("172.27.0.138", 5679))

    ptvsd.wait_for_attach()
    _LOGGER.info("Debugger is attached!")

GATEWAY = "GATEWAY"
USERNAME = "--user"
PASSWORD = "--pass"


async def main(loop):
    """Return the JSON as requested."""

    args = docopt(__doc__)
    # print(args)

    # session is optional, but without it: ERROR: Unclosed client session
    session = aiohttp.ClientSession()

    gateway = InComfortGateway(
        hostname=args[GATEWAY],
        username=args[USERNAME],
        password=args[PASSWORD],
        session=session,
        debug=DEBUG_MODE
    )

    # gateway.fake_heater = True
    try:
        heaters = await gateway.heaters
    except aiohttp.ClientResponseError as err:
        _LOGGER.warning("Setup failed, check your configuration, message is: %s", err)
        await session.close()
        return

    for heater in heaters:
        # heater.fake_room = True
        await heater.update()

        # print(f"Raw JSON = {heater._data}")
        print(f"Status = {heater.status}")
        print(f"Display = {heater.display_code}({heater.display_text})")
        print(f"Fault code = {heater.fault_code}")

    if session:
        await session.close()


if __name__ == "__main__":  # called from CLI?
    LOOP = asyncio.get_event_loop()
    LOOP.run_until_complete(main(LOOP))
    LOOP.close()
