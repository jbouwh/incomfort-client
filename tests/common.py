"""Python client library for the InterGas InComfort system (via Lan2RF gateway)."""

from aiohttp import ClientSession

from incomfortclient import HEATERLIST, Gateway, Heater

SERIAL_NO_0 = "2110f25190"
SERIAL_NO_1 = "2110f25191"
SERIAL_NO_2 = "2303\\02041"
SERIAL_NO_2_CORRECTED = "2303002041"

GATEWAYS_WITH_HEATER = (
    {HEATERLIST: [SERIAL_NO_0, None, None, None, None, None, None, None]},
)


async def gwy_with_heaterlist(gateway: str) -> Gateway:
    """Request the heaterlist from a mocked gateway."""

    async with ClientSession() as session:
        gwy = Gateway(gateway, session=session)
        await gwy.heaters()

    return gwy


async def heater_with_status(gateway: str) -> Heater:
    """Update the heater status from a mocked gateway."""

    async with ClientSession() as session:
        gwy = Gateway(gateway, session=session)
        heaters = await gwy.heaters()
        await heaters[0].update()

    return heaters[0]
