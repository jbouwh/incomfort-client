"""Python client library for the InterGas InComfort system (via Lan2RF gateway).

   Each Gateway can have up to 8 Heaters (boilers) and each Heater can have 0-2
   Room thermostats.
   """

CLIENT_TIMEOUT = 20  # seconds

INVALID_VALUE = (2 ** 15 - 1) / 100.0  # 127 * 256 + 255 = 327.67
SERIAL_LINE = "0123456789abcdefghijklmnopqrstuvwxyz"

# key label: IO
BITMASK_BURNER = 0x08  # burner state: on / off
BITMASK_FAIL = 0x01  # failure state: on / off (aka lockout)
BITMASK_PUMP = 0x02  # pump state: on / off
BITMASK_TAP = 0x04  # tap (DHW) state: function on / off

# key label: displ_code
DISPLAY_CODES = {
    0: "opentherm",
    15: "boiler ext.",
    24: "frost",
    37: "central heating rf",
    51: "tapwater int.",
    85: "sensortest",
    102: "central heating",
    126: "standby",
    153: "postrun boiler",
    170: "service",
    204: "tapwater",
    231: "postrun ch",
    240: "boiler int.",
    255: "buffer",
}
FAULT_CODES = {
    0: "Sensor fault after self check",
    1: "Temperature too high",
    2: "S1 and S2 interchanged",
    4: "No flame signal",
    5: "Poor flame signal",
    6: "Flame detection fault",
    8: "Incorrect fan speed",
    10: "Sensor fault S1",
    11: "Sensor fault S1",
    12: "Sensor fault S1",
    13: "Sensor fault S1",
    14: "Sensor fault S1",
    20: "Sensor fault S2",
    21: "Sensor fault S2",
    22: "Sensor fault S2",
    23: "Sensor fault S2",
    24: "Sensor fault S2",
    27: "Shortcut outside sensor temperature",
    29: "Gas valve relay faulty",
    30: "Gas valve relay faulty",
}  # "0.0": "Low system pressure"

HEATER_ATTRS = [
    "display_code",
    "display_text",
    "fault_code",
    "is_burning",
    "is_failed",
    "is_pumping",
    "is_tapping",
    "heater_temp",
    "tap_temp",
    "pressure",
    "serial_no",
]
ROOM_ATTRS = ["room_temp", "setpoint", "override"]

OVERRIDE_MAX_TEMP = 30.0
OVERRIDE_MIN_TEMP = 5.0
