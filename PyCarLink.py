import base64
from urllib import response
import requests
from requests import Request, RequestException
import logging
import time
import sys
import json

def base64_encode(string: str) -> str:
    '''
    Encodes the provided byte string into base64
    :param string: A byte string to be encoded. Pass in as b'string to encode'
    :return: a base64 encoded byte string
    '''
    return base64.b64encode(string)


BASE_URL = "https://api.m2msuite.com/v1.1/109.3/"

log = logging.getLogger(__name__)

class PyCarlink(object):
    # Connects to Carlink

    def __init__(self, email, password):
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
        response = requests.get(url, headers=self.login_auth_header)
        json_data = response.json()
        # Pull API key and Account ID from response
        return json_data["APIKey"]

    def retrieve_account_id(self):
        url = BASE_URL + '100007/Access'
        response = requests.get(url, headers=self.login_auth_header)
        json_data = response.json()      
        # Pull API key and Account ID from response
        return json_data["AccountID"]

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
        response = requests.get(url, headers=self.api_auth_header)
        json_data = response.json()      
        # Pull API key and Account ID from response. This will only return 
        # the first asset from this response, I don't have the knowledge to 
        # add multiples
        return json_data[0]["ID"]
    
    def get_asset_status(self):
        url = BASE_URL + str(self.account_id) + '/DeviceStatus/' + str(self.asset_id)
        response = requests.get(url, headers=self.api_auth_header)
        json_data = response.json()
        self.gpsstatus = json_data['GpsStatus']
        self.gpsdatetime = json_data['GpsDateTime']
        self.latitude = json_data["Latitude"]
        self.longitude = json_data["Longitude"]
        self.speed = json_data["Speed"]
        self.heading = json_data["Heading"]
        self.externalvoltage = json_data['ExternalVoltage']
        self.rssi = json_data["Rssi"]
        self.doorstatus = json_data['DoorStatus']
        self.enginestatus = json_data['EngineStatus']
        self.ingnitionstatus = json_data['IgnitionStatus']
        self.alarm = json_data['Alarm']
        self.engineshutdowndatetime = json_data['EngineShutdownDateTime']
        self.bypassupdateddatetime = json_data['BypassUpdatedDateTime']
        self.bypasstemperature = json_data["BypassTemperature"]
        self.online = json_data['Online']
     
        return json_data

    def start_engine(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"EngineStart"}
        response = requests.post(url, json=body, headers=self.api_auth_header)
        data = response.json()
        self.command_id = data['ID']
        time.sleep(10)
        getstatus = self.command_status(self.command_id)
        if "Success" not in getstatus:
            time.sleep(10)
            getstatus = self.command_status(self.command_id)
            if "Success" not in getstatus:
                return "Command Failed"
        else:
            return getstatus


    def stop_engine(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"EngineStop"}
        response = requests.post(url, json=body, headers=self.api_auth_header)
        data = response.json()
        self.command_id = data['ID']
        time.sleep(10)
        getstatus = self.command_status(self.command_id)
        if "Success" not in getstatus:
            time.sleep(10)
            getstatus = self.command_status(self.command_id)
            if "Success" not in getstatus:
                return "Command Failed"
        else:
            return getstatus


    def lock_doors(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"DoorLock"}
        response = requests.post(url, json=body, headers=self.api_auth_header)
        data = response.json()
        self.command_id = data['ID']
        time.sleep(10)
        getstatus = self.command_status(self.command_id)
        if "Success" not in getstatus:
            time.sleep(10)
            getstatus = self.command_status(self.command_id)
            if "Success" not in getstatus:
                return "Command Failed"
        else:
            return getstatus


    def unlock_doors(self):
        url = BASE_URL + str(self.account_id) + '/Commands'
        body = {"DeviceID":self.asset_id,"Type":"DoorUnLock"}
        response = requests.post(url, json=body, headers=self.api_auth_header)
        data = response.json()
        self.command_id = data['ID']
        time.sleep(10)
        getstatus = self.command_status(self.command_id)
        if "Success" not in getstatus:
            time.sleep(10)
            getstatus = self.command_status(self.command_id)
            if "Success" not in getstatus:
                return "Command Failed"
        else:
            return getstatus

    def command_status(self, command_id):
        command_id_status = command_id
        url = BASE_URL + str(self.account_id) + '/Commands/' + str(command_id_status)
        statusresponse = requests.get(url, headers=self.api_auth_header)
        json_response = statusresponse.json()
        status = json_response['Status']
        return status
