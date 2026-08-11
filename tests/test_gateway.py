"""Python client library for the InterGas InComfort system (via Lan2RF gateway)."""

from aiohttp import ClientError

import pytest
from common import (
    SERIAL_NO_0,
    SERIAL_NO_1,
    SERIAL_NO_2,
    SERIAL_NO_2_CORRECTED,
    gwy_with_heaterlist,
)

from incomfortclient import (
    HEATERLIST,
    NULL_SERIAL_NO,
    InvalidGateway,
    InvalidHeaterList,
)

# Test data...
GATEWAYS_SANS_HEATERS = (
    {HEATERLIST: [None, None, None, None, None, None, None, None]},
    {HEATERLIST: [NULL_SERIAL_NO, None, None, None, None, None, None, None]},
    {HEATERLIST: [NULL_SERIAL_NO, NULL_SERIAL_NO, None, None, None, None, None, None]},
)

GATEWAYS_WITH_HEATERS = (
    {HEATERLIST: [SERIAL_NO_0, None, None, None, None, None, None, None]},
    {HEATERLIST: [SERIAL_NO_0, SERIAL_NO_1, None, None, None, None, None, None]},
    {HEATERLIST: [None, NULL_SERIAL_NO, None, None, SERIAL_NO_0, None, None, None]},
)

# pylint: disable=protected-access


@pytest.mark.parametrize(
    "heater_list_exc", [ClientError, UnicodeDecodeError, TimeoutError]
)
async def test_gateway_invalid(gateway: str) -> None:
    """Test an invalid gateway request."""
    try:
        await gwy_with_heaterlist(gateway)
    except InvalidGateway:
        return
    raise AssertionError


@pytest.mark.parametrize("heater_list", GATEWAYS_SANS_HEATERS)
async def test_heaterlist_empty(gateway: str) -> None:
    """Test the gateway with an empty heater list."""
    try:
        await gwy_with_heaterlist(gateway)
    except InvalidHeaterList:
        return
    raise AssertionError


@pytest.mark.parametrize("heater_list", GATEWAYS_WITH_HEATERS)
async def test_heaterlist_valid(gateway: str) -> None:
    """Test the gateway with a valid heater list."""
    gwy = await gwy_with_heaterlist(gateway)

    assert gwy._heaters and gwy._heaters[0].serial_no == SERIAL_NO_0
    assert len(gwy._heaters) < 2 or gwy._heaters[1].serial_no == SERIAL_NO_1


@pytest.mark.parametrize(
    "heater_list",
    ['{"heaterlist":' f'["{SERIAL_NO_2}",null,null,null,null,null,null,null]' "}"],
)
async def test_heaterlist_valid_alt_sn(gateway: str) -> None:
    """Test the gateway with a valid heater list."""
    gwy = await gwy_with_heaterlist(gateway)

    assert gwy._heaters and gwy._heaters[0].serial_no == SERIAL_NO_2_CORRECTED
    assert len(gwy._heaters) < 2 or gwy._heaters[1].serial_no == SERIAL_NO_2_CORRECTED
