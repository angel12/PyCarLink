# PyCarLink
Python Library for Carlink / mycarcontrols.com / CL6

This is a work in progress, and since I'm not a programmer by trade, my code is bound to be sloppy and innefecient!

Currently this library is working with the following features:

- Logging into CL6 unofficial API
- Getting the status of the first asset (vehicle) listed under your account, which includes:
    -   gpsstatus
    -   gpsdatetime
    -   latitude
    -   longitude
    -   speed
    -   heading
    -   externalvoltage
    -   rssi
    -   doorstatus
    -   enginestatus
    -   ingnitionstatus
    -   alarm
    -   engineshutdowndatetime
    -   bypassupdateddatetime
    -   bypasstemperature
    -   online
- Sending the following Commands:
    -   start_engine
    -   stop_engine
    -   lock_doors
    -   unlock_doors

This is an unoficial API implementation, so this project could stop working at any moment.

Usage

from a python shell:

- Initial Setup

`from PyCarlink import PyCarlink`

`email = 'example@email.com'`

`password = 'yourpassword'`

`client = PyCarlink(email, password)`

- Available Commands

Get the status of your vehicle in a json format

`client.get_asset_status()`

Start your engine. Returns either Success or Failure

`client.start_engine()`

Stop your engine. Returns either Success or Failure

`client.stop_engine()`

Lock Your Doors. Returns either Success or Failure

`client.lock_doors()`

Unlock Your Doors. Returns either Success or Failure

`client.unlock_doors()`

## HTTP timeout policy and ambiguous commands

Every HTTP GET and POST, including requests during construction and command
polling, uses a `(connect, read)` timeout in seconds. The default is `(5.0, 30.0)`;
existing `PyCarlink(email, password)` calls remain valid. Configure both limits
when constructing the client:

```python
client = PyCarlink(email, password, timeout=(3.0, 20.0))
```

The timeout must be a two-element tuple of positive finite Python `int` or `float`
values within the float range. Invalid values (including `None`, zero, negative
values, booleans, NaN, and infinity) raise `ValueError` before any network request.

`requests.exceptions.Timeout` (including `ConnectTimeout` and `ReadTimeout`)
propagates unchanged to the caller, including from the constructor. Catch it
around construction or individual operations as appropriate. PyCarLink does not
automatically retry timed-out requests. In particular, a command POST may have
reached the vehicle even if its response timed out: do **not** blindly resubmit
it. A polling timeout also leaves the command outcome unknown; it does not cause
another command POST.

These are Requests connect and read-inactivity limits, **not** a total wall-clock
deadline for an operation. DNS resolution, multiple connection attempts,
redirects, and a response that keeps delivering data can extend elapsed time;
existing command polling sleeps are separate from the HTTP limits.
