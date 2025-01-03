#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

Each Gateway can have up to 8 Heaters (boilers) and each Heater can have 0-2
Room thermostats.
"""

import argparse
import asyncio
import logging

import aiohttp

from incomfortclient import Gateway

logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s %(levelname)-8s: %(message)s",
    level=logging.WARNING,
)
_LOGGER = logging.getLogger(__name__)

DEBUG_MODE = False
DEBUG_ADDR = "0.0.0.0"
DEBUG_PORT = 5678

if DEBUG_MODE is True:
    import debugpy

    _LOGGER.setLevel(logging.DEBUG)

    debugpy.listen(address=(DEBUG_ADDR, DEBUG_PORT))
    print(f"Debugging is enabled, listening on: {DEBUG_ADDR}:{DEBUG_PORT}.")
    print(" - execution paused, waiting for debugger to attach...")

    debugpy.wait_for_client()
    print(" - debugger is now attached, continuing execution.")


DEFAULT_HEATER_NO = 0
DEFAULT_ROOM_NO = 0


def _parse_args():
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

    parser.add_argument(
        "-H",
        "--heater",
        type=int,
        required=False,
        default=DEFAULT_HEATER_NO,
        help="select heater (0, 1, 2, 3, 4 or 5)",
    )
    parser.add_argument(
        "-R",
        "--room",
        type=int,
        required=False,
        default=DEFAULT_ROOM_NO,
        help="select room thermostat (0, 1 or 2)",
    )

    args = parser.parse_args()

    if bool(args.username) ^ bool(args.password):
        parser.error("--username and --password must be given together, or not at all")
        return None

    return args


async def main():
    """Return the JSON as requested."""

    args = _parse_args()

    if not args:
        return False

    # session is optional, but without it: ERROR: Unclosed client session
    session = aiohttp.ClientSession()

    gateway = Gateway(
        args.gateway,
        session=session,
        username=args.username,
        password=args.password,
        debug=DEBUG_MODE,
    )

    try:
        heaters = list(await gateway.heaters())
    except aiohttp.ClientResponseError as err:
        _LOGGER.warning("Setup failed, check your configuration, message is: %s", err)
        await session.close()
        return False

    if ((heater := int(args.heater)) + 1) > (nr_heaters := len(heaters)):
        print(
            f"Nr of heaters found: {nr_heaters}. "
            f"Heater index {args.heater} is invalid"
        )
        await session.close()
        return

    heater = heaters[heater]
    await heater.update()

    if ((room := int(args.room)) + 1) > (nr_rooms := len(heater.rooms)):
        print(
            f"Nr of rooms found for heater: {nr_rooms}. "
            f"Room index {args.room} is invalid"
        )
        await session.close()
        return

    if args.temp:
        try:
            await heater.rooms[room].set_override(args.temp)
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

    await session.close()


if __name__ == "__main__":  # called from CLI?
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
    loop.close()
