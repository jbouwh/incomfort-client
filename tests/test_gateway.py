#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Python client library for the InterGas InComfort system (via Lan2RF gateway)."""

from __future__ import annotations

import pytest
from common import HOSTNAME, SERIAL_NO_0, SERIAL_NO_1, gwy_with_heaterlist

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


@pytest.mark.asyncio
async def test_gateway_invalid():
    try:
        await gwy_with_heaterlist(None)
    except InvalidGateway:
        return
    raise AssertionError


@pytest.mark.asyncio
@pytest.mark.parametrize("index", range(len(GATEWAYS_SANS_HEATERS)))
async def test_heaterlist_empty(index, gateways=GATEWAYS_SANS_HEATERS):
    try:
        await gwy_with_heaterlist(HOSTNAME, heaterlist=gateways[index])
    except InvalidHeaterList:
        return
    raise AssertionError


@pytest.mark.asyncio
@pytest.mark.parametrize("index", range(len(GATEWAYS_WITH_HEATERS)))
async def test_heaterlist_valid(index, gateways=GATEWAYS_WITH_HEATERS):
    gwy = await gwy_with_heaterlist(HOSTNAME, heaterlist=gateways[index])

    assert gwy._heaters[0].serial_no == SERIAL_NO_0
    assert len(gwy._heaters) < 2 or gwy._heaters[1].serial_no == SERIAL_NO_1
