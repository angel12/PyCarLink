import unittest
from unittest.mock import Mock, patch

from pycarlink.PyCarLink import PyCarlink


STATUS_FIELDS = {
    'gpsstatus': 'GpsStatus',
    'gpsdatetime': 'GpsDateTime',
    'latitude': 'Latitude',
    'longitude': 'Longitude',
    'speed': 'Speed',
    'heading': 'Heading',
    'externalvoltage': 'ExternalVoltage',
    'rssi': 'Rssi',
    'doorstatus': 'DoorStatus',
    'enginestatus': 'EngineStatus',
    'ingnitionstatus': 'IgnitionStatus',
    'alarm': 'Alarm',
    'engineshutdowndatetime': 'EngineShutdownDateTime',
    'bypassupdateddatetime': 'BypassUpdatedDateTime',
    'bypasstemperature': 'BypassTemperature',
    'online': 'Online',
}


def status_payload(version):
    return {field: '{}-{}'.format(field, version)
            for field in STATUS_FIELDS.values()}


class StatusSnapshotTests(unittest.TestCase):
    def setUp(self):
        # Guard the transport too: no unmocked request may reach the service.
        transport = patch('requests.sessions.Session.request',
                          side_effect=AssertionError('Unexpected network request'))
        transport.start()
        self.addCleanup(transport.stop)
        get = patch('pycarlink.PyCarLink.requests.get')
        self.get = get.start()
        self.addCleanup(get.stop)

    def make_client(self, initial):
        self.get.side_effect = [
            Mock(json=Mock(return_value={'APIKey': 'test-key'})),
            Mock(json=Mock(return_value={'AccountID': 123})),
            Mock(json=Mock(return_value=[{'ID': 456}])),
            Mock(json=Mock(return_value=initial)),
        ]
        return PyCarlink('offline@example.invalid', 'not-a-real-password')

    def assert_snapshot(self, client, payload):
        self.assertEqual(client.asset_status, payload)
        for attribute, field in STATUS_FIELDS.items():
            with self.subTest(attribute=attribute):
                self.assertEqual(getattr(client, attribute), payload[field])

    def test_constructor_and_repeated_refresh_keep_snapshot_consistent(self):
        initial = status_payload('initial')
        client = self.make_client(initial)
        self.assert_snapshot(client, initial)
        for version in ('second', 'third'):
            refreshed = status_payload(version)
            refreshed['ExtraField'] = version
            self.get.side_effect = None
            self.get.return_value = Mock(json=Mock(return_value=refreshed))
            result = client.get_asset_status()
            self.assertEqual(result, refreshed)
            self.assertEqual(client.asset_status, result)
            self.assert_snapshot(client, refreshed)

    def test_incomplete_refresh_preserves_entire_previous_snapshot(self):
        for missing_field in STATUS_FIELDS.values():
            with self.subTest(missing_field=missing_field):
                initial = status_payload('initial')
                client = self.make_client(initial)
                previous_state = vars(client).copy()
                incomplete = status_payload('changed')
                del incomplete[missing_field]
                self.get.side_effect = None
                self.get.return_value = Mock(json=Mock(return_value=incomplete))

                with self.assertRaises(KeyError):
                    client.get_asset_status()

                self.assertEqual(vars(client), previous_state)
                self.assertIs(client.asset_status, initial)
                self.assert_snapshot(client, initial)


if __name__ == '__main__':
    unittest.main()
