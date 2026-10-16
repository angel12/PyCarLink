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

Start your engine. See command outcomes below.

`client.start_engine()`

Stop your engine. See command outcomes below.

`client.stop_engine()`

Lock Your Doors. See command outcomes below.

`client.lock_doors()`

Unlock Your Doors. See command outcomes below.

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

### Command outcomes

All four command methods submit the physical command once, retain its ID in
`client.command_id`, and poll its status at most twice, waiting 10 seconds before
each poll. They return:

- `"Success"`: the API reported exactly `Success` on either poll.
- `"Command Failed"`: the API reported a terminal failure code; polling stops
  immediately, including when the first poll reports failure.
- `"Command Timed Out"`: both polls were unresolved (`Pending` or `Processing`).
  This replaces the old `"Command Failed"` result for exhausted pending polls.
  It means the outcome is **unknown**, not that the vehicle command failed or
  was cancelled. It describes polling exhaustion, not an HTTP request timeout.

The [M2M Suite v1.1 command-status documentation](https://www.m2msuite.com/Api/Ajax/v1.1/application/commands?uri=1&method=get)
defines the required `Status` as “Success, Pending, Processing or a failure code”.
For responses conforming to that contract, this library assumes other status
values are terminal failure codes, not additional pending states. The source
does not enumerate specific failure codes; test failure values are synthetic.
This assumption would need revisiting if the API adds nonterminal states.

No command is automatically resubmitted. After a timeout, save the command ID
before submitting another command (which overwrites `client.command_id`) and
check the existing command later with `client.command_status(command_id)`.
That method returns the raw API status without submitting a physical command.
Do not blindly retry a physical action: the original may still execute.
These behaviors are covered by offline tests; live vehicle execution has not
been verified.
