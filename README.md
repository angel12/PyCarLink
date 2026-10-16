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

Installation

Install from a checkout of this repository (this also installs `requests`):

```sh
git clone https://github.com/angel12/PyCarLink.git
cd PyCarLink
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install .
```

Usage

From a Python shell in the environment where you installed the package (no need
to stay in the checkout directory). Importing does not contact the service;
constructing a client logs in and retrieves vehicle data.

- Initial Setup

`from pycarlink import PyCarlink`

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
