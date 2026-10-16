"""Offline regression tests for issue #3; no service or vehicle is contacted."""
import unittest
from unittest.mock import Mock, patch

import requests

from pycarlink.PyCarLink import PyCarlink


class TimeoutTests(unittest.TestCase):
    commands = ('start_engine', 'stop_engine', 'lock_doors', 'unlock_doors')
    status = dict.fromkeys((
        'GpsStatus', 'GpsDateTime', 'Latitude', 'Longitude', 'Speed', 'Heading',
        'ExternalVoltage', 'Rssi', 'DoorStatus', 'EngineStatus', 'IgnitionStatus',
        'Alarm', 'EngineShutdownDateTime', 'BypassUpdatedDateTime',
        'BypassTemperature', 'Online'), 0)

    def setUp(self):
        # Fail closed even if production code bypasses the mocked GET/POST calls.
        for target in ('requests.sessions.Session.request', 'socket.socket'):
            guard = patch(target, side_effect=AssertionError('Real network forbidden'))
            guard.start()
            self.addCleanup(guard.stop)
        get = patch('pycarlink.PyCarLink.requests.get', side_effect=self.respond)
        post = patch('pycarlink.PyCarLink.requests.post', return_value=Mock(
            json=Mock(return_value={'ID': 'command'})))
        sleep = patch('pycarlink.PyCarLink.time.sleep')
        self.get = get.start()
        self.post = post.start()
        self.sleep = sleep.start()
        for patcher in (get, post, sleep):
            self.addCleanup(patcher.stop)

    def respond(self, url, **kwargs):
        if url.endswith('/Access'):
            data = {'APIKey': 'offline-key', 'AccountID': 'account'}
        elif url.endswith('/Assets'):
            data = [{'ID': 'asset'}]
        elif '/DeviceStatus/' in url:
            data = self.status.copy()
        else:
            data = {'Status': 'Success'}
        return Mock(json=Mock(return_value=data))

    def assert_policy_on_all_paths(self, client, policy):
        # Constructor covers both Access calls, asset discovery and device status.
        self.assertEqual(self.get.call_count, 4)
        for method in self.commands:
            with self.subTest(method=method):
                self.assertEqual(getattr(client, method)(), 'Success')
        self.assertEqual(self.get.call_count, 8)
        self.assertEqual(self.post.call_count, 4)
        for call in self.get.call_args_list + self.post.call_args_list:
            self.assertEqual(call.kwargs.get('timeout'), policy)

    def test_two_argument_constructor_sets_finite_policy_on_all_paths(self):
        client = PyCarlink('offline@example.invalid', 'dummy')
        self.assert_policy_on_all_paths(client, (5.0, 30.0))

    def test_custom_connect_read_policy_on_all_paths(self):
        client = PyCarlink('offline@example.invalid', 'dummy', timeout=(1.5, 7))
        self.assert_policy_on_all_paths(client, (1.5, 7))

    def test_invalid_policy_is_rejected_before_network(self):
        invalid = [None, 1, '5', [], (), (1,), (1, 2, 3), [1, 2]]
        for value in (None, 0, -1, float('inf'), float('-inf'), float('nan'),
                      True, False, '5', object()):
            invalid.extend(((value, 1), (1, value)))
        for policy in invalid:
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, 'timeout'):
                    PyCarlink('offline@example.invalid', 'dummy', timeout=policy)
                self.get.assert_not_called()
                self.post.assert_not_called()

    def test_constructor_propagates_timeout_at_each_get_without_retry(self):
        for error_type in (requests.ConnectTimeout, requests.ReadTimeout):
            for stage in range(4):
                with self.subTest(error=error_type.__name__, stage=stage):
                    error = error_type('offline timeout')
                    self.get.reset_mock()
                    calls = 0

                    def fail_at_stage(url, **kwargs):
                        nonlocal calls
                        calls += 1
                        if calls == stage + 1:
                            raise error
                        return self.respond(url, **kwargs)

                    self.get.side_effect = fail_at_stage
                    with self.assertRaises(error_type) as caught:
                        PyCarlink('offline@example.invalid', 'dummy')
                    self.assertIs(caught.exception, error)
                    self.assertEqual(self.get.call_count, stage + 1)
                    self.post.assert_not_called()

    def test_each_get_propagates_timeout_without_retry(self):
        client = PyCarlink('offline@example.invalid', 'dummy')
        paths = [('retrieve_api_key', ()), ('retrieve_account_id', ()),
                 ('get_asset_0', ()), ('get_asset_status', ()),
                 ('command_status', ('command',))]
        for error_type in (requests.ConnectTimeout, requests.ReadTimeout):
            for method, args in paths:
                with self.subTest(error=error_type.__name__, method=method):
                    error = error_type('offline timeout')
                    self.get.reset_mock()
                    self.get.side_effect = error
                    with self.assertRaises(error_type) as caught:
                        getattr(client, method)(*args)
                    self.assertIs(caught.exception, error)
                    self.get.assert_called_once()
                    self.assertEqual(self.get.call_args.kwargs['timeout'], (5.0, 30.0))

    def test_each_post_propagates_timeout_without_retry_or_poll(self):
        client = PyCarlink('offline@example.invalid', 'dummy')
        self.get.reset_mock()
        for error_type in (requests.ConnectTimeout, requests.ReadTimeout):
            for method in self.commands:
                with self.subTest(error=error_type.__name__, method=method):
                    error = error_type('offline timeout')
                    self.post.reset_mock()
                    self.post.side_effect = error
                    with self.assertRaises(error_type) as caught:
                        getattr(client, method)()
                    self.assertIs(caught.exception, error)
                    self.post.assert_called_once()
                    self.assertEqual(self.post.call_args.kwargs['timeout'], (5.0, 30.0))
                    self.get.assert_not_called()
                    self.sleep.assert_not_called()

    def test_poll_timeout_does_not_resubmit_command(self):
        client = PyCarlink('offline@example.invalid', 'dummy')
        for method in self.commands:
            with self.subTest(method=method):
                self.get.reset_mock()
                self.post.reset_mock()
                error = requests.ReadTimeout('offline poll timeout')
                self.get.side_effect = error
                with self.assertRaises(requests.ReadTimeout) as caught:
                    getattr(client, method)()
                self.assertIs(caught.exception, error)
                self.post.assert_called_once()
                self.get.assert_called_once()


if __name__ == '__main__':
    unittest.main()
