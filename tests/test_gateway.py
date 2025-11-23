#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Python client library for the InterGas InComfort system (via Lan2RF gateway)."""

from __future__ import annotations

import pytest
from common import (
    GATEWAYS_WITH_HEATER,
    HOSTNAME,
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


@pytest.mark.asyncio
async def test_gateway_invalid() -> None:
    """Test an invalid gateway."""
    try:
        await gwy_with_heaterlist(None, GATEWAYS_WITH_HEATER[0])
    except InvalidGateway:
        return
    raise AssertionError


@pytest.mark.asyncio
@pytest.mark.parametrize("index", range(len(GATEWAYS_SANS_HEATERS)))
async def test_heaterlist_empty(index: int) -> None:
    """Test the gateway with an empty heater list."""
    try:
        await gwy_with_heaterlist(HOSTNAME, heaterlist=GATEWAYS_SANS_HEATERS[index])
    except InvalidHeaterList:
        return
    raise AssertionError


@pytest.mark.asyncio
@pytest.mark.parametrize("index", range(len(GATEWAYS_WITH_HEATERS)))
async def test_heaterlist_valid(index: int) -> None:
    """Test the gateway with a valid heater list."""
    gwy = await gwy_with_heaterlist(HOSTNAME, heaterlist=GATEWAYS_WITH_HEATERS[index])

    assert gwy._heaters and gwy._heaters[0].serial_no == SERIAL_NO_0
    assert len(gwy._heaters) < 2 or gwy._heaters[1].serial_no == SERIAL_NO_1


@pytest.mark.asyncio
async def test_heaterlist_valid_alt_sn() -> None:
    """Test the gateway with a valid heater list."""
    heaterlist_response = (
        '{"heaterlist":' f'["{SERIAL_NO_2}",null,null,null,null,null,null,null]' "}"
    )
    gwy = await gwy_with_heaterlist(HOSTNAME, heaterlist=heaterlist_response)

    assert gwy._heaters and gwy._heaters[0].serial_no == SERIAL_NO_2_CORRECTED
    assert len(gwy._heaters) < 2 or gwy._heaters[1].serial_no == SERIAL_NO_2_CORRECTED
