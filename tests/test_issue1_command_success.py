"""Offline regression coverage for issue #1 command return values."""

import unittest
from unittest.mock import Mock, call, patch

from pycarlink.PyCarLink import BASE_URL, PyCarlink


class CommandSuccessTests(unittest.TestCase):
    COMMANDS = (
        ("start_engine", "EngineStart"),
        ("stop_engine", "EngineStop"),
        ("lock_doors", "DoorLock"),
        ("unlock_doors", "DoorUnLock"),
    )

    def assert_command_result(self, method, command_type, statuses, expected):
        # Bypass initialization, which otherwise authenticates against the API.
        client = PyCarlink.__new__(PyCarlink)
        client.account_id = 123
        client.asset_id = 456
        client.api_auth_header = {"Authorization": "offline-test"}
        responses = [Mock() for _ in statuses]
        for response, status in zip(responses, statuses):
            response.json.return_value = {"Status": status}

        with (
            patch("pycarlink.PyCarLink.requests.post") as post,
            patch("pycarlink.PyCarLink.requests.get", side_effect=responses) as get,
            patch("pycarlink.PyCarLink.time.sleep") as sleep,
        ):
            post.return_value.json.return_value = {"ID": 789}
            result = getattr(client, method)()
            self.assertEqual(result, expected)
            post.assert_called_once_with(
                BASE_URL + "123/Commands",
                json={"DeviceID": 456, "Type": command_type},
                headers=client.api_auth_header,
            )
            self.assertEqual(client.command_id, 789)
            self.assertEqual(
                get.call_args_list,
                [call(BASE_URL + "123/Commands/789", headers=client.api_auth_header)]
                * len(statuses),
            )
            self.assertEqual(sleep.call_args_list, [call(10)] * len(statuses))

    def test_first_poll_success(self):
        for method, command_type in self.COMMANDS:
            with self.subTest(method=method):
                self.assert_command_result(method, command_type, ["Success"], "Success")

    def test_second_poll_success(self):
        for method, command_type in self.COMMANDS:
            with self.subTest(method=method):
                self.assert_command_result(
                    method, command_type, ["Pending", "Success"], "Success"
                )

    def test_unsuccessful_polls_preserve_failure_result(self):
        for method, command_type in self.COMMANDS:
            with self.subTest(method=method):
                self.assert_command_result(
                    method, command_type, ["Pending", "Pending"], "Command Failed"
                )


if __name__ == "__main__":
    unittest.main()
