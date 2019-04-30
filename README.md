# intouch-client

Python client library for **Intergas InTouch-compatible boilers** accesible via a **Lan2RF gateway**. It includes a basic CLI to demonstrate how to use the library.

### Porting from syncio libraries
This library is based upon https://github.com/bwesterb/incomfort, but uses **aiohttp** rather than synchronous I/O (such as **requests** or **httplib**).

Where possible, it uses uses the same methods and properties as **incomfort**, but with the following differences:

  Classes:
  - `InTouchGateway` renamed from Gateway
    - added kwargs: `username`, `password` (used for later versions of firmware)

  - `InTouchHeater` renamed from Heater
    - renamed: `is_burning`, `is_failed`, `is_pumping`, `is_tapping`
    - moved out: `room_temp`, `setpoint`, `setpoint_override`, `set`
    - new/added: `update`, `status`, `rooms`

  - `InTouchRoom` has been added, and some methods moved in from Heater
    - same name: `room_temp`, `setpoint`
    - renamed: `override`, `set_override`
    - new/added: `status`
