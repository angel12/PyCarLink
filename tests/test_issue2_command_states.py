"""Offline command-state tests; failure codes below are synthetic, not API enums."""

import unittest
from unittest.mock import Mock, call, patch

from pycarlink.PyCarLink import BASE_URL, PyCarlink


class CommandStateTests(unittest.TestCase):
    COMMANDS = (
        ("start_engine", "EngineStart"),
        ("stop_engine", "EngineStop"),
        ("lock_doors", "DoorLock"),
        ("unlock_doors", "DoorUnLock"),
    )

    def setUp(self):
        # Any accidentally unmocked requests call must fail before network I/O.
        network = patch("requests.sessions.Session.request",
                        side_effect=AssertionError("Real network is forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def assert_outcome(self, statuses, expected):
        for method, command_type in self.COMMANDS:
            with self.subTest(method=method, statuses=statuses):
                with (
                    patch.object(PyCarlink, "retrieve_api_key", return_value="offline-key"),
                    patch.object(PyCarlink, "retrieve_account_id", return_value=123),
                    patch.object(PyCarlink, "get_asset_0", return_value=456),
                    patch.object(PyCarlink, "get_asset_status", return_value={}),
                ):
                    client = PyCarlink("offline@example.invalid", "dummy")
                responses = [Mock() for _ in statuses]
                for response, status in zip(responses, statuses):
                    response.json.return_value = {"Status": status}
                with (
                    patch("pycarlink.PyCarLink.requests.post") as post,
                    patch("pycarlink.PyCarLink.requests.get",
                          side_effect=responses + [responses[-1]]) as get,
                    patch("pycarlink.PyCarLink.time.sleep") as sleep,
                ):
                    post.return_value.json.return_value = {"ID": 789}
                    result = getattr(client, method)()
                    self.assertEqual(result, expected)
                    post.assert_called_once()
                    self.assertEqual(post.call_args.args, (BASE_URL + "123/Commands",))
                    self.assertEqual(post.call_args.kwargs["json"],
                                     {"DeviceID": 456, "Type": command_type})
                    self.assertEqual(client.command_id, 789)
                    self.assertEqual(get.call_count, len(statuses))
                    for request in get.call_args_list:
                        self.assertEqual(request.args, (BASE_URL + "123/Commands/789",))
                    self.assertEqual(sleep.call_args_list, [call(10)] * len(statuses))

    def test_success_must_be_exact_on_either_poll(self):
        for prefix in ([], ["Pending"], ["Processing"]):
            self.assert_outcome(prefix + ["NotSuccess"], "Command Failed")

    def test_first_poll_success(self):
        self.assert_outcome(["Success"], "Success")

    def test_second_poll_success(self):
        for first in ("Pending", "Processing"):
            self.assert_outcome([first, "Success"], "Success")

    def test_terminal_failure_stops_on_first_poll(self):
        self.assert_outcome(["SyntheticFailureCode"], "Command Failed")

    def test_terminal_failure_on_second_poll(self):
        for first in ("Pending", "Processing"):
            self.assert_outcome([first, "SyntheticFailureCode"], "Command Failed")

    def test_unresolved_pending_and_processing_time_out(self):
        for first in ("Pending", "Processing"):
            for second in ("Pending", "Processing"):
                self.assert_outcome([first, second], "Command Timed Out")


if __name__ == "__main__":
    unittest.main()
