#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Python client library for the InterGas InComfort system (via Lan2RF gateway)."""

from __future__ import annotations

import aiohttp
from aioresponses import aioresponses

from incomfortclient import HEATERLIST, Gateway, Heater

HOSTNAME = "192.168.0.1"

SERIAL_NO_0 = "2110f25190"
SERIAL_NO_1 = "2110f25191"

GATEWAYS_WITH_HEATER = (
    {HEATERLIST: [SERIAL_NO_0, None, None, None, None, None, None, None]},
)


async def gwy_with_heaterlist(hostname, heaterlist=GATEWAYS_WITH_HEATER[0]) -> Gateway:
    """Request the heaterlist from a mocked gateway."""

    with aioresponses() as mocked:
        if hostname:
            mocked.get(
                f"http://{hostname}/heaterlist.json",
                payload=heaterlist,
            )

        async with aiohttp.ClientSession() as session:
            gwy = Gateway(hostname or HOSTNAME, session=session)
            await gwy.heaters()

    return gwy


async def heater_with_status(data_heater, heaterlist=GATEWAYS_WITH_HEATER[0]) -> Heater:
    """Update the heater status from a mocked gateway."""

    with aioresponses() as mocked:
        mocked.get(
            f"http://{HOSTNAME}/heaterlist.json",
            payload=heaterlist,
        )
        mocked.get(
            f"http://{HOSTNAME}/data.json?heater=0",
            payload=data_heater,
        )

        async with aiohttp.ClientSession() as session:
            gwy = Gateway(HOSTNAME, session=session)
            heaters = await gwy.heaters()
            await heaters[0].update()

    return heaters[0]
