#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Python client library for the InterGas InComfort system (via Lan2RF gateway)."""

from __future__ import annotations

import pytest

from common import SERIAL_NO_0, heater_status


# Test data...
HEATER_SANS_ROOMS = (
    {
        "serial_year": 0,
        "serial_month": 0,
        "serial_line": 0,
        "serial_sn1": 0,
        "serial_sn2": 0,
        "serial_sn3": 0,

        "displ_code": 126,
        "IO": 0,

        "ch_temp_lsb": 168,
        "ch_temp_msb": 24,
        "tap_temp_lsb": 184,
        "tap_temp_msb": 19,
        "ch_pressure_lsb": 174,
        "ch_pressure_msb": 0,

        "nodenr": 250,
        "rf_message_rssi": 27,
        "rfstatus_cntr": 0,

        "room_set_ovr_1_msb": 0,
        "room_set_ovr_1_lsb": 0,
        "room_temp_1_lsb": 108,
        "room_temp_1_msb": 7,
        "room_temp_set_1_lsb": 8,
        "room_temp_set_1_msb": 7,

        "room_set_ovr_2_msb": 3,
        "room_set_ovr_2_lsb": 132,
        "room_temp_2_lsb": 255,
        "room_temp_2_msb": 127,
        "room_temp_set_2_lsb": 255,
        "room_temp_set_2_msb": 127,
    },
    {
        "serial_no": SERIAL_NO_0,

        "display_code": 126,
        "display_text": "standby",
        "fault_code": None,
        "is_burning": False,
        "is_failed": False,
        "is_pumping": False,
        "is_tapping": False,

        "heater_temp": 63.12,
        "tap_temp": 50.48,
        "pressure": 1.74,

        "nodenr": 250,
        "rf_message_rssi": 27,
        "rfstatus_cntr": 0,

        # "room_1": None,
        # "room_2": None,
    },
)


@pytest.mark.asyncio
async def test_heater_sans_rooms():

    status = await heater_status(HEATER_SANS_ROOMS[0])
    assert status == HEATER_SANS_ROOMS[1]


# @pytest.mark.asyncio
# async def test_heater_with_rooms():

#     status = await heater_status(HEATER_WITH_ROOMS[0])
#     assert status == HEATER_WITH_ROOMS[1]
