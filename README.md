# intouch-client

Python client library for **Intergas InTouch-compatible boilers** accesible via a **Lan2RF gateway**. It includes a basic CLI to demonstrate how to use the library.

### Porting from syncio libraries
This library is based upon https://github.com/bwesterb/incomfort, but uses **aiohttp** rather than synchronous I/O (such as **requests** or **httplib**).

Where possible, it uses uses the same methods and properties as **incomfort**, but with the following differences:

  - `InTouchGateway` class renamed from Gateway
    - added kwargs: `username`, `password` (used for later versions of firmware)

  - `InTouchHeater` class renamed from Heater
    - renamed: `is_burning`, `is_failed`, `is_pumping`, `is_tapping`
    - moved out: `room_temp`, `setpoint`, `setpoint_override`, `set`
    - new/added: `update`, `status`, `rooms`

  - `InTouchRoom` class has been added, and some methods moved in from Heater
    - same name: `room_temp`, `setpoint`
    - renamed: `override`, `set_override`
    - new/added: `status`

### Basic CLI included
There is a very basic CLI (the output has been formatted here for readability):
```bash
(venv) root@hostname:~/client_apis/intouch-client$ python intouchclient/__init__.py ${HOSTNAME}
{
  'display_code': 126, 
  'display_text': 'standby', 
  'fault_code': 0, 
  
  'is_burning': False, 
  'is_failed': False,
  'is_pumping': False, 
  'is_tapping': False, 
  
  'heater_temp': 31.22, 
  'tap_temp': 27.91, 
  'pressure': 1.23, 
  'serial_no': '175t23072', 
  
  'nodenr': 200, 
  'rf_message_rssi': 38, 
  'rfstatus_cntr': 0, 
  
  'room_1': {'room_temp': 26.4, 'setpoint': 19.5, 'override': 19.5}, 
  'room_2': {'room_temp': None, 'setpoint': None, 'override': 19.0}
}
```
