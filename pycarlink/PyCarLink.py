import base64
from urllib import response
import requests
from requests import Request, RequestException
import logging
import time
import sys
import json
#
# Carlink uses m2msuite for their application / API. Documentation can be found here:
# https://www.m2msuite.com/Api/Rest
# 
# I am a very green (read: new) programmer, so this code is more than likely just plain messy 
# and inefficient. Feel free to help clean it up.
#
# Projects I used as guidelines for this project:
# pycarwings2 - https://github.com/filcole/pycarwings2
# pymazda - https://github.com/bdr99/pymazda
#

#
# From https://stackoverflow.com/a/56081104
#
def base64_encode(string: str) -> str:
    '''
    Encodes the provided byte string into base64
    :param string: A byte string to be encoded. Pass in as b'string to encode'
    :return: a base64 encoded byte string
    '''
    return base64.b64encode(string)


BASE_URL = "https://api.m2msuite.com/v1.1/109.3/"

log = logging.getLogger(__name__)

class MalformedResponseError(ValueError):
    """The service returned JSON or response fields this client cannot use."""


class NoAssetsError(ValueError):
    """The account has no assets for this client to select."""


def _parse_response(response, expected_type: type = dict):
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError:
        raise MalformedResponseError('Response must contain valid JSON.') from None
    if not isinstance(data, expected_type):
        shape = 'array' if expected_type is list else 'object'
        raise MalformedResponseError('Response must be a JSON ' + shape + '.')
    return data


def _required_field(data, field, identifier=False):
    if not isinstance(data, dict):
        raise MalformedResponseError('Response item must be a JSON object.')
    if field not in data:
        raise MalformedResponseError('Response is missing required field ' + field + '.')
    value = data[field]
    valid = isinstance(value, str) and bool(value.strip())
    if identifier:
        valid = valid or type(value) is int
    if not valid:
        expected = 'a nonempty string or integer' if identifier else 'a nonempty string'
        raise MalformedResponseError('Response field ' + field + ' must be ' + expected + '.')
    return value


class PyCarlink(object):
    # Connects to Carlink

    def __init__(self, email, password, timeout=(5.0, 30.0)):
        if (not isinstance(timeout, tuple) or len(timeout) != 2
                or any(type(value) not in (int, float)
                       or not 0 < value <= sys.float_info.max for value in timeout)):
            raise ValueError('timeout must be a (connect, read) tuple of positive finite seconds')
        self.timeout = timeout
        self.email = email
        self.password = password
        self.login_auth_header = None
        self.api_key = None
        self.account_id = None
        self.asset_id = None

        self.login_auth_header = self.create_login_header(email, password)

        self.api_key = self.retrieve_api_key()
        self.account_id = self.retrieve_account_id()
        self.api_auth_header = self.create_api_header()
        self.asset_id = self.get_asset_0()
        self.asset_status = self.get_asset_status()

    def create_login_header(self, email, password):
    #
    # Carlink expects login info in Authorization header, login info is combined email, ":", password, 
    # for example: example@example.com:password
    # 
        login = self.email + ':' + self.password
    #
    # Once combined, it needs to be encoded to base64, so the example above would be:
    # example@example.com:password  =  ZXhhbXBsZUBleGFtcGxlLmNvbTpwYXNzd29yZA==
    #
        encodedlogin = login.encode("utf-8")
        base64login = base64_encode(encodedlogin)
        base64_str = str(base64login)
    #
    # Due to my inexperience, this is how I have to handle the login info getting extra characters from encoding
    #
        bas64_rstrip = base64_str.rstrip(base64_str[-1])
        base64_strip = bas64_rstrip[2:]
        auth_string = 'Basic' + ' ' + base64_strip
        self.login_auth_header = {'Authorization': auth_string}
        return self.login_auth_header
#
#   Carlink only uses your login info to retrieve the api key and account ID, 
#   all other commands require your api key
#
    def retrieve_api_key(self):
        url = BASE_URL + '100007/Access'
        response = requests.get(url, headers=self.login_auth_header, timeout=self.timeout)
        json_data = _parse_response(response)
        # Pull API key and Account ID from response
        return _required_field(json_data, 'APIKey')

    def retrieve_account_id(self):
        url = BASE_URL + '100007/Access'
        response = requests.get(url, headers=self.login_auth_header, timeout=self.timeout)
        json_data = _parse_response(response)
        # Pull API key and Account ID from response
        return _required_field(json_data, 'AccountID', identifier=True)

    def create_api_header(self):
        api_key_base = '@apikey:' + self.api_key
        api_encode = api_key_base.encode("utf-8")
        api_base64 = base64_encode(api_encode)
        api_str = str(api_base64)
        api_rstrip = api_str.rstrip(api_str[-1])
        api_strip = api_rstrip[2:]
        auth_string = 'Basic ' + api_strip
        self.api_auth_header = {'Authorization': auth_string}
        return self.api_auth_header

    def get_asset_0(self):
        url = BASE_URL + str(self.account_id) + '/Assets'
        response = requests.get(url, headers=self.api_auth_header, timeout=self.timeout)
        json_data = _parse_response(response, list)
        # Pull API key and Account ID from response. This will only return 
        # the first asset from this response, I don't have the knowledge to 
        # add multiples
        if not json_data:
            raise NoAssetsError('Account has no assets; add a vehicle before using this client.')
        return _required_field(json_data[0], 'ID', identifier=True)
    
    def get_asset_status(self):
        url = BASE_URL + str(self.account_id) + '/DeviceStatus/' + str(self.asset_id)
        response = requests.get(url, headers=self.api_auth_header, timeout=self.timeout)
        json_data = _parse_response(response)
        # Read every required field before publishing any part of the snapshot.
        required = (
            'GpsStatus', 'GpsDateTime', 'Latitude', 'Longitude', 'Speed', 'Heading',
            'ExternalVoltage', 'Rssi', 'DoorStatus', 'EngineStatus', 'IgnitionStatus',
            'Alarm', 'EngineShutdownDateTime', 'BypassUpdatedDateTime',
            'BypassTemperature', 'Online',
        )
        for field in required:
            if field not in json_data:
                raise MalformedResponseError(
                    'DeviceStatus response is missing required field ' + field + '.')
        status = {
            'gpsstatus': json_data['GpsStatus'],
            'gpsdatetime': json_data['GpsDateTime'],
            'latitude': json_data['Latitude'],
            'longitude': json_data['Longitude'],
            'speed': json_data['Speed'],
            'heading': json_data['Heading'],
            'externalvoltage': json_data['ExternalVoltage'],
            'rssi': json_data['Rssi'],
            'doorstatus': json_data['DoorStatus'],
            'enginestatus': json_data['EngineStatus'],
            'ingnitionstatus': json_data['IgnitionStatus'],
            'alarm': json_data['Alarm'],
            'engineshutdowndatetime': json_data['EngineShutdownDateTime'],
            'bypassupdateddatetime': json_data['BypassUpdatedDateTime'],
            'bypasstemperature': json_data['BypassTemperature'],
            'online': json_data['Online'],
            'asset_status': json_data,
        }
        self.__dict__.update(status)

        return json_data

    def start_engine(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"EngineStart"}
        response = requests.post(url, json=body, headers=self.api_auth_header, timeout=self.timeout)
        data = _parse_response(response)
        self.command_id = _required_field(data, 'ID', identifier=True)
        return self._poll_command(self.command_id)


    def stop_engine(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"EngineStop"}
        response = requests.post(url, json=body, headers=self.api_auth_header, timeout=self.timeout)
        data = _parse_response(response)
        self.command_id = _required_field(data, 'ID', identifier=True)
        return self._poll_command(self.command_id)


    def lock_doors(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"DoorLock"}
        response = requests.post(url, json=body, headers=self.api_auth_header, timeout=self.timeout)
        data = _parse_response(response)
        self.command_id = _required_field(data, 'ID', identifier=True)
        return self._poll_command(self.command_id)


    def unlock_doors(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"DoorUnLock"}
        response = requests.post(url, json=body, headers=self.api_auth_header, timeout=self.timeout)
        data = _parse_response(response)
        self.command_id = _required_field(data, 'ID', identifier=True)
        return self._poll_command(self.command_id)

    def _poll_command(self, command_id):
        """Poll an existing command; exhaustion does not establish failure."""
        for _ in range(2):
            time.sleep(10)
            status = self.command_status(command_id)
            if status == "Success":
                return status
            # API contract: Success, Pending, Processing or a failure code.
            # Assume other statuses are failure codes, not new pending states.
            if status not in ("Pending", "Processing"):
                return "Command Failed"
        return "Command Timed Out"

    def command_status(self, command_id):
        command_id_status = command_id
        url = BASE_URL + str(self.account_id) + '/Commands/' + str(command_id_status)
        statusresponse = requests.get(url, headers=self.api_auth_header, timeout=self.timeout)
        json_response = _parse_response(statusresponse)
        status = _required_field(json_response, 'Status')
        return status
