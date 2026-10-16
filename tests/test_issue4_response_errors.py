import json
import unittest
from unittest.mock import Mock, patch

import requests
import pycarlink.PyCarLink as library


STATUS_KEYS = (
    'GpsStatus', 'GpsDateTime', 'Latitude', 'Longitude', 'Speed', 'Heading',
    'ExternalVoltage', 'Rssi', 'DoorStatus', 'EngineStatus', 'IgnitionStatus',
    'Alarm', 'EngineShutdownDateTime', 'BypassUpdatedDateTime',
    'BypassTemperature', 'Online',
)
GET_PATHS = ('retrieve_api_key', 'retrieve_account_id', 'get_asset_0',
             'get_asset_status', 'command_status')
POST_PATHS = ('start_engine', 'stop_engine', 'lock_doors', 'unlock_doors')


def response(payload=None, status=200, raw=None):
    result = requests.Response()
    result.status_code = status
    result.url = 'https://example.invalid/offline'
    result._content = (json.dumps(payload) if raw is None else raw).encode()
    return result


class ResponseErrorsTests(unittest.TestCase):
    def setUp(self):
        for target, name in (
            ('requests.sessions.Session.request', 'transport'),
            ('pycarlink.PyCarLink.requests.get', 'get'),
            ('pycarlink.PyCarLink.requests.post', 'post'),
            ('pycarlink.PyCarLink.time.sleep', 'sleep'),
        ):
            mocker = patch(target, side_effect=AssertionError('Unexpected call'))
            setattr(self, name, mocker.start())
            self.addCleanup(mocker.stop)
        self.client = object.__new__(library.PyCarlink)
        self.client.__dict__.update(
            login_auth_header={'Authorization': 'secret-login'},
            api_auth_header={'Authorization': 'secret-api'},
            account_id=123, asset_id=456, command_id='previous',
            asset_status={'previous': True})

    def invoke(self, method):
        args = ('command',) if method == 'command_status' else ()
        return getattr(self.client, method)(*args)

    def supply(self, method, result):
        self.get.reset_mock()
        self.post.reset_mock()
        self.sleep.reset_mock()
        self.get.side_effect = AssertionError('Unexpected GET')
        self.post.side_effect = AssertionError('Unexpected POST')
        target = self.post if method in POST_PATHS else self.get
        target.side_effect = None
        target.return_value = result

    def test_constructor_validates_each_stage_and_stops_on_failure(self):
        valid = [{'APIKey': 'offline-key'}, {'AccountID': 'account'},
                 [{'ID': 'asset'}], dict.fromkeys(STATUS_KEYS)]
        for stage in range(4):
            for bad, error in (
                (response(status=401), requests.HTTPError),
                (response(status=500), requests.HTTPError),
                (response(raw='secret-body'), library.MalformedResponseError),
                (response(None), library.MalformedResponseError),
                (response([{}] if stage == 2 else {}), library.MalformedResponseError),
            ):
                with self.subTest(stage=stage, error=error):
                    self.get.reset_mock()
                    self.get.side_effect = [response(v) for v in valid[:stage]] + [bad]
                    with self.assertRaises(error):
                        library.PyCarlink('offline@example.invalid', 'offline-password')
                    self.assertEqual(self.get.call_count, stage + 1)
        self.get.side_effect = [response(v) for v in valid[:2]] + [response([])]
        with self.assertRaises(library.NoAssetsError):
            library.PyCarlink('offline@example.invalid', 'offline-password')
        self.post.assert_not_called()

    def test_success_accepts_string_and_integer_ids_and_nullable_telemetry(self):
        for identifier in ('id-123', 123, 0):
            self.get.side_effect = [response({'APIKey': 'offline-key'}),
                                    response({'AccountID': identifier}),
                                    response([{'ID': identifier}]),
                                    response(dict.fromkeys(STATUS_KEYS))]
            client = library.PyCarlink('offline@example.invalid', 'offline-password')
            self.assertEqual(client.account_id, identifier)
            self.assertEqual(client.asset_id, identifier)
            self.assertEqual(client.asset_status, dict.fromkeys(STATUS_KEYS))
            self.assertIsNone(client.bypasstemperature)
            for method in POST_PATHS:
                self.post.side_effect = None
                self.post.return_value = response({'ID': identifier})
                self.get.side_effect = [response({'Status': 'Success'})]
                self.sleep.side_effect = None
                self.assertEqual(getattr(client, method)(), 'Success')
                self.assertEqual(client.command_id, identifier)

    def test_network_exceptions_propagate_unchanged_without_retry(self):
        for method in GET_PATHS + POST_PATHS:
            for error in (requests.Timeout('offline timeout'),
                          requests.ConnectionError('offline connection')):
                with self.subTest(method=method, error=error):
                    self.supply(method, response({}))
                    target = self.post if method in POST_PATHS else self.get
                    target.side_effect = error
                    before = vars(self.client).copy()
                    with self.assertRaises(type(error)) as caught:
                        self.invoke(method)
                    self.assertIs(caught.exception, error)
                    self.assertEqual(target.call_count, 1)
                    self.assertEqual(vars(self.client), before)
                    if method in POST_PATHS:
                        self.get.assert_not_called()
                        self.sleep.assert_not_called()

    def test_poll_errors_propagate_after_one_successful_submission(self):
        for method in POST_PATHS:
            for bad, error in ((response(status=500), requests.HTTPError),
                               (response(raw='secret-body'), library.MalformedResponseError),
                               (response({}), library.MalformedResponseError)):
                with self.subTest(method=method, error=error):
                    self.supply(method, response({'ID': 'accepted'}))
                    self.get.side_effect = None
                    self.get.return_value = bad
                    self.sleep.side_effect = None
                    with self.assertRaises(error):
                        self.invoke(method)
                    self.post.assert_called_once()
                    self.get.assert_called_once()
                    self.assertEqual(self.client.command_id, 'accepted')

    def test_empty_assets_has_specific_actionable_error(self):
        error_type = getattr(library, 'NoAssetsError', None)
        self.assertIsNotNone(error_type, 'Missing NoAssetsError contract')
        self.supply('get_asset_0', response([]))
        with self.assertRaisesRegex(error_type, 'asset'):
            self.client.get_asset_0()

    def test_required_fields_reject_missing_or_invalid_values(self):
        paths = {'retrieve_api_key': 'APIKey', 'retrieve_account_id': 'AccountID',
                 'get_asset_0': 'ID', 'command_status': 'Status'}
        paths.update({method: 'ID' for method in POST_PATHS})
        for method, field in paths.items():
            invalid_values = [None, True, False, [], {}, '', '   ', 1.5]
            if field in ('APIKey', 'Status'):
                invalid_values.append(123)
            for payload in [{}] + [{field: value} for value in invalid_values]:
                with self.subTest(method=method, payload=payload):
                    if method == 'get_asset_0':
                        payload = [payload]
                    self.supply(method, response(payload))
                    before = vars(self.client).copy()
                    with self.assertRaises(library.MalformedResponseError) as caught:
                        self.invoke(method)
                    self.assertIn(field, str(caught.exception))
                    self.assertEqual(vars(self.client), before)
                    if method in POST_PATHS:
                        self.get.assert_not_called()
                        self.sleep.assert_not_called()
        for item in (None, [], True, 'secret-body', 123):
            self.supply('get_asset_0', response([item]))
            with self.assertRaises(library.MalformedResponseError):
                self.client.get_asset_0()

    def test_wrong_top_level_shape_is_rejected_everywhere(self):
        for method in GET_PATHS + POST_PATHS:
            invalid = (None, True, 42, 'secret-body', {}) if method == 'get_asset_0' else (None, True, 42, 'secret-body', [])
            for payload in invalid:
                with self.subTest(method=method, payload=payload):
                    self.supply(method, response(payload))
                    before = vars(self.client).copy()
                    with self.assertRaises(library.MalformedResponseError) as caught:
                        self.invoke(method)
                    self.assertNotIn('secret', str(caught.exception))
                    self.assertEqual(vars(self.client), before)
                    if method in POST_PATHS:
                        self.get.assert_not_called()
                        self.sleep.assert_not_called()

    def test_non_json_is_a_safe_actionable_library_error(self):
        error_type = getattr(library, 'MalformedResponseError', None)
        self.assertIsNotNone(error_type, 'Missing MalformedResponseError contract')
        for method in GET_PATHS + POST_PATHS:
            with self.subTest(method=method):
                self.supply(method, response(raw='secret-body secret-login secret-api'))
                before = vars(self.client).copy()
                with self.assertRaises(error_type) as caught:
                    self.invoke(method)
                self.assertIn('JSON', str(caught.exception))
                self.assertNotIn('secret', str(caught.exception))
                self.assertEqual(vars(self.client), before)
                if method in POST_PATHS:
                    self.get.assert_not_called()
                    self.sleep.assert_not_called()

    def test_http_errors_precede_json_for_every_response_site(self):
        for method in GET_PATHS + POST_PATHS:
            for status in (401, 500):
                with self.subTest(method=method, status=status):
                    result = response(status=status, raw='not JSON secret-body')
                    result.json = Mock(side_effect=AssertionError('JSON before HTTP'))
                    self.supply(method, result)
                    before = vars(self.client).copy()
                    with self.assertRaises(requests.HTTPError) as caught:
                        self.invoke(method)
                    self.assertIs(caught.exception.response, result)
                    result.json.assert_not_called()
                    self.assertEqual(vars(self.client), before)
                    if method in POST_PATHS:
                        self.get.assert_not_called()
                        self.sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
