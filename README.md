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
