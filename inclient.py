"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

   Each Gateway can have up to 8 Heaters (boilers) and each Heater can have 0-2
   Room thermostats.
   """

import argparse
import asyncio
import logging

import aiohttp

from incomfortclient import Gateway as InComfortGateway

logging.basicConfig(
    datefmt="%H:%M:%S", format="%(asctime)s %(levelname)-8s: %(message)s"
)
_LOGGER = logging.getLogger(__name__)

DEBUG_MODE = True

if DEBUG_MODE is True:
    import ptvsd  # pylint: disable=import-error

    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.info("Waiting for debugger to attach...")
    ptvsd.enable_attach(address=("172.27.0.138", 5679))

    ptvsd.wait_for_attach()
    _LOGGER.info("Debugger is attached!")

DEFAULT_HEATER_NO = 0
DEFAULT_ROOM_NO = 2


async def main(loop):
    """Return the JSON as requested."""

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

    # session is optional, but without it: ERROR: Unclosed client session
    session = aiohttp.ClientSession()

    gateway = InComfortGateway(
        args.gateway,
        session=session,
        username=args.username,
        password=args.password,
        debug=DEBUG_MODE,
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

    heater = heaters[DEFAULT_HEATER_NO]

    if args.temp:
        try:
            await heater.rooms[DEFAULT_ROOM_NO].set_override(args.temp)
        except IndexError:
            _LOGGER.error("IndexError - Hint: There is no valid room thermostat")
            raise

    elif args.raw:
        print(heater._data)  # pylint: disable=protected-access

    else:
        status = dict(heater.status)
        for room in heater.rooms:
            status[f"room_{room.room_no}"] = room.status
        print(status)

    if session:
        await session.close()


if __name__ == "__main__":  # called from CLI?
    LOOP = asyncio.get_event_loop()
    LOOP.run_until_complete(main(LOOP))
    LOOP.close()
